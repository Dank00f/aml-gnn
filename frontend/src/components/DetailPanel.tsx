'use client'

import { useState } from 'react'
import { Badge, Box, Flex, IconButton, Progress, ScrollArea, Text, Tooltip } from '@radix-ui/themes'
import { Cross2Icon } from '@radix-ui/react-icons'
import type { NodeData } from '@/types/graph/node'
import type { EdgeData } from '@/types/graph/edge'
import type { DetectorResult } from '@/types/graph/detector'
import type { NodeScoringResult, ScoreMode } from '@/types/graph/analysis'

const ENTITY_COLORS: Record<string, string> = {
  client: 'blue',
  account: 'green',
  company: 'orange',
  device: 'purple',
  unknown: 'gray'
}

const PATTERN_LABELS: Record<string, string> = {
  cycles: 'Транзакционный цикл',
  fanout: 'Веерное дробление',
  transit: 'Транзитный узел',
  shared_device: 'Общее устройство/IP'
}

interface DetailPanelProps {
  node: NodeData
  allNodes: NodeData[]
  edges: EdgeData[]
  detectorResults: DetectorResult[]
  scoring: NodeScoringResult | null
  activeScoreMode: ScoreMode
  activeNodeScore: number | null
  onClose: () => void
  onSelectNode: (node: NodeData) => void
}

type RiskLevel = 'high' | 'medium' | 'low'

function riskLevel(score: number): RiskLevel {
  if (score > 0.7) return 'high'
  if (score > 0.3) return 'medium'
  return 'low'
}

const RISK_COLOR: Record<RiskLevel, 'red' | 'amber' | 'green'> = {
  high: 'red',
  medium: 'amber',
  low: 'green'
}

const RISK_LABEL: Record<RiskLevel, string> = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий'
}

const SCORE_MODE_LABEL: Record<ScoreMode, string> = {
  rule_based: 'Rule',
  gnn: 'GNN'
}

function getPatternsForNode(nodeId: string, results: DetectorResult[]): string[] {
  return results
    .filter(r =>
      r.items.some(item => {
        if (Array.isArray(item.node_ids) && (item.node_ids as string[]).includes(nodeId))
          return true
        if (Array.isArray(item.nodes) && (item.nodes as string[]).includes(nodeId)) return true
        if (item.node_id === nodeId) return true
        if (item.source_node === nodeId) return true
        if (Array.isArray(item.receivers) && (item.receivers as string[]).includes(nodeId))
          return true
        return false
      })
    )
    .map(r => r.pattern_type)
}

function formatMoney(value: number, currency?: string): string {
  const formatted = value.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
  return currency ? `${formatted} ${currency}` : formatted
}

function formatTimestamp(value: number): string {
  if (!value) return 'нет даты'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('ru-RU')
}

function edgeKey(edge: EdgeData): string {
  return edge.id ?? `${edge.source}-${edge.target}-${edge.timestamp}`
}

function formatAttribute(value: unknown): string {
  if (value === null || value === undefined) return 'нет'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function Section({ children }: { children: React.ReactNode }) {
  return (
    <Flex
      direction="column"
      gap="2"
      p="3"
      style={{ borderBottom: '1px solid var(--gray-4)', minWidth: 0 }}
    >
      {children}
    </Flex>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Text
      size="1"
      weight="medium"
      color="gray"
      style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
    >
      {children}
    </Text>
  )
}

function KVRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <Flex justify="between" gap="2" style={{ minWidth: 0 }}>
      <Text size="2" color="gray" style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Text
        size="2"
        style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          textAlign: 'right',
          fontFamily: mono ? 'var(--font-mono)' : undefined
        }}
      >
        {value}
      </Text>
    </Flex>
  )
}

export default function DetailPanel({
  node,
  allNodes,
  edges,
  detectorResults,
  scoring,
  activeScoreMode,
  activeNodeScore,
  onClose,
  onSelectNode
}: DetailPanelProps) {
  const [selectedEdgeKey, setSelectedEdgeKey] = useState<string | null>(null)
  const nodeMap = new Map(allNodes.map(n => [n.id, n]))
  const scoreMap = new Map(
    allNodes.map((currentNode, index) => [
      currentNode.id,
      scoring?.scores[index] ?? currentNode.risk_score ?? 0
    ])
  )
  const outgoing = edges.filter(e => e.source === node.id)
  const incoming = edges.filter(e => e.target === node.id)
  const relatedEdges = [...outgoing, ...incoming]
  const neighborIds = new Set([...outgoing.map(e => e.target), ...incoming.map(e => e.source)])
  const neighbors = [...neighborIds].map(id => nodeMap.get(id)).filter(Boolean) as NodeData[]

  const patterns = getPatternsForNode(node.id, detectorResults)
  const computedInFlow = incoming.reduce((s, e) => s + e.amount_paid, 0)
  const computedOutFlow = outgoing.reduce((s, e) => s + e.amount_paid, 0)
  const displayInFlow = node.in_flow
  const displayOutFlow = node.out_flow
  const flowBalance = displayInFlow - displayOutFlow

  const maxFlow = Math.max(computedInFlow, computedOutFlow, 1)
  const balanceDev = Math.abs(computedInFlow - computedOutFlow) / maxFlow
  const totalDegree = outgoing.length + incoming.length
  const score = activeNodeScore ?? scoreMap.get(node.id) ?? node.risk_score ?? 0
  const level = riskLevel(score)

  const currency =
    [...outgoing, ...incoming].find(e => e.payment_currency)?.payment_currency ?? undefined

  return (
    <Flex
      direction="column"
      style={{
        width: 256,
        flexShrink: 0,
        minWidth: 0,
        borderLeft: '1px solid var(--gray-4)',
        background: 'var(--color-panel-solid)',
        overflow: 'hidden' // prevents the panel itself from being wider than 256px
      }}
    >
      <Flex
        align="center"
        justify="between"
        px="3"
        py="2"
        style={{ borderBottom: '1px solid var(--gray-4)', flexShrink: 0 }}
      >
        <Tooltip content={node.id}>
          <Text
            size="2"
            weight="medium"
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: 160
            }}
          >
            {node.id}
          </Text>
        </Tooltip>
        <IconButton variant="ghost" color="gray" size="1" onClick={onClose}>
          <Cross2Icon />
        </IconButton>
      </Flex>

      <ScrollArea scrollbars="vertical" style={{ flex: 1 }}>
        <Box style={{ width: '100%', maxWidth: '100%', minWidth: 0, overflow: 'hidden' }}>
          <Section>
            <Badge
              color={
                ENTITY_COLORS[node.entity_type] as 'blue' | 'green' | 'orange' | 'purple' | 'gray'
              }
              variant="soft"
              size="1"
            >
              {node.entity_type}
            </Badge>
            <Flex align="center" justify="between" style={{ minWidth: 0 }}>
              <Text size="2" color="gray" style={{ flexShrink: 0 }}>
                Риск-скор
              </Text>
              <Badge color={RISK_COLOR[level]} variant="soft" size="1">
                {Math.round(score * 100)}% - {RISK_LABEL[level]}
              </Badge>
            </Flex>
            <Badge color="gray" variant="soft" size="1" style={{ width: 'fit-content' }}>
              {SCORE_MODE_LABEL[activeScoreMode]}
            </Badge>
            <Progress value={score * 100} color={RISK_COLOR[level]} size="1" />
          </Section>

          <Section>
            <SectionLabel>Финансовый профиль</SectionLabel>
            {node.is_laundering_node && (
              <Badge color="red" variant="solid" size="1">
                ⚠ Ground truth: отмывание
              </Badge>
            )}
            <KVRow label="Входящий поток" value={formatMoney(displayInFlow, currency)} />
            <KVRow label="Исходящий поток" value={formatMoney(displayOutFlow, currency)} />
            <Flex justify="between" gap="2" style={{ minWidth: 0 }}>
              <Text size="2" color="gray" style={{ flexShrink: 0 }}>
                Баланс
              </Text>
              <Text
                size="2"
                style={{
                  fontVariantNumeric: 'tabular-nums',
                  textAlign: 'right',
                  color: flowBalance >= 0 ? 'var(--green-11)' : 'var(--red-11)'
                }}
              >
                {flowBalance >= 0 ? '+' : ''}
                {formatMoney(flowBalance, currency)}
              </Text>
            </Flex>
          </Section>

          <Section>
            <SectionLabel>Вклад факторов</SectionLabel>
            <RiskRow label="Степень узла" value={Math.min(totalDegree / 20, 1)} weight={0.25} />
            <RiskRow label="Цикл" value={patterns.includes('cycles') ? 1 : 0} weight={0.4} />
            <RiskRow label="Дисбаланс" value={balanceDev} weight={0.2} />
            <RiskRow
              label="Общ. устройство"
              value={patterns.includes('shared_device') ? 1 : 0}
              weight={0.15}
            />
          </Section>

          {node.alerts.length > 0 && (
            <Section>
              <SectionLabel>Алерты ({node.alerts.length})</SectionLabel>
              <Flex wrap="wrap" gap="1">
                {node.alerts.map((a, i) => (
                  <Badge
                    key={i}
                    color="red"
                    variant="soft"
                    size="1"
                    style={{
                      maxWidth: '100%',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {a}
                  </Badge>
                ))}
              </Flex>
            </Section>
          )}

          {patterns.length > 0 && (
            <Section>
              <SectionLabel>Обнаружен в паттернах</SectionLabel>
              <Flex wrap="wrap" gap="1">
                {patterns.map(p => (
                  <Badge key={p} color="amber" variant="soft" size="1">
                    {PATTERN_LABELS[p] ?? p}
                  </Badge>
                ))}
              </Flex>
            </Section>
          )}

          {Object.keys(node.attributes).length > 0 && (
            <Section>
              <SectionLabel>Атрибуты</SectionLabel>
              {Object.entries(node.attributes).map(([k, v]) => (
                <KVRow key={k} label={k} value={String(v)} />
              ))}
            </Section>
          )}

          <Section>
            <SectionLabel>Транзакции</SectionLabel>
            <Flex gap="2">
              <Box
                style={{
                  flex: 1,
                  background: 'var(--gray-3)',
                  borderRadius: 'var(--radius-2)',
                  padding: 'var(--space-2)',
                  minWidth: 0
                }}
              >
                <Text size="1" color="gray" as="div">
                  Исходящие
                </Text>
                <Text size="3" weight="bold" as="div">
                  {outgoing.length}
                </Text>
                <Text
                  size="1"
                  color="gray"
                  as="div"
                  style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {computedOutFlow.toLocaleString('ru-RU', { maximumFractionDigits: 0 })}
                </Text>
              </Box>
              <Box
                style={{
                  flex: 1,
                  background: 'var(--gray-3)',
                  borderRadius: 'var(--radius-2)',
                  padding: 'var(--space-2)',
                  minWidth: 0
                }}
              >
                <Text size="1" color="gray" as="div">
                  Входящие
                </Text>
                <Text size="3" weight="bold" as="div">
                  {incoming.length}
                </Text>
                <Text
                  size="1"
                  color="gray"
                  as="div"
                  style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {computedInFlow.toLocaleString('ru-RU', { maximumFractionDigits: 0 })}
                </Text>
              </Box>
            </Flex>

            {relatedEdges.slice(0, 12).map(edge => {
              const key = edgeKey(edge)
              const isSelected = selectedEdgeKey === key
              const isOutgoing = edge.source === node.id
              const counterpartyId = isOutgoing ? edge.target : edge.source
              const counterparty = nodeMap.get(counterpartyId)
              return (
                <Box
                  key={key}
                  onClick={() => setSelectedEdgeKey(isSelected ? null : key)}
                  style={{
                    background: 'var(--gray-2)',
                    border: isSelected ? '1px solid var(--accent-8)' : '1px solid var(--gray-4)',
                    borderRadius: 'var(--radius-2)',
                    padding: '6px 8px',
                    minWidth: 0,
                    cursor: 'pointer'
                  }}
                >
                  <Flex direction="column" gap="1" style={{ minWidth: 0 }}>
                    <Flex justify="between" gap="2" align="center">
                      <Badge color={isOutgoing ? 'blue' : 'green'} variant="soft" size="1">
                        {isOutgoing ? 'Исходящая' : 'Входящая'}
                      </Badge>
                      <Flex align="center" gap="2">
                        <Text size="1" color="gray" style={{ fontVariantNumeric: 'tabular-nums' }}>
                          {formatMoney(edge.amount_paid, edge.payment_currency ?? undefined)}
                        </Text>
                        <Badge color={isSelected ? 'blue' : 'gray'} variant="soft" size="1">
                          {isSelected ? 'Скрыть' : 'Детали'}
                        </Badge>
                      </Flex>
                    </Flex>
                    <Text
                      size="1"
                      style={{
                        fontFamily: 'var(--font-mono)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {edge.id ?? `${edge.source} -> ${edge.target}`}
                    </Text>
                    <Flex justify="between" gap="2" align="center" style={{ minWidth: 0 }}>
                      <Text size="1" color="gray" style={{ flexShrink: 0 }}>
                        {isOutgoing ? 'Кому' : 'От кого'}
                      </Text>
                      <Text
                        size="1"
                        onClick={event => {
                          event.stopPropagation()
                          if (counterparty) onSelectNode(counterparty)
                        }}
                        style={{
                          cursor: counterparty ? 'pointer' : 'default',
                          textDecoration: counterparty ? 'underline' : undefined,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontFamily: 'var(--font-mono)'
                        }}
                      >
                        {counterpartyId}
                      </Text>
                    </Flex>
                    <KVRow label="Дата" value={formatTimestamp(edge.timestamp)} />
                    {edge.payment_format && <KVRow label="Формат" value={edge.payment_format} />}
                    {edge.alerts.length > 0 && (
                      <Badge color="red" variant="soft" size="1">
                        alerts: {edge.alerts.length}
                      </Badge>
                    )}
                    {isSelected && (
                      <Flex
                        direction="column"
                        gap="1"
                        mt="1"
                        style={{
                          borderTop: '1px solid var(--gray-5)',
                          paddingTop: 6,
                          minWidth: 0
                        }}
                      >
                        <KVRow label="ID" value={edge.id ?? key} mono />
                        <KVRow label="Отправитель" value={edge.source} mono />
                        <KVRow label="Получатель" value={edge.target} mono />
                        <KVRow
                          label="Списано"
                          value={formatMoney(edge.amount_paid, edge.payment_currency ?? undefined)}
                        />
                        {edge.amount_received !== null && edge.amount_received !== undefined && (
                          <KVRow
                            label="Получено"
                            value={formatMoney(
                              edge.amount_received,
                              edge.receiving_currency ?? undefined
                            )}
                          />
                        )}
                        <KVRow label="Risk" value={`${Math.round(edge.risk_score * 100)}%`} />
                        {edge.is_laundering !== null && edge.is_laundering !== undefined && (
                          <KVRow
                            label="Label"
                            value={edge.is_laundering ? 'Is Laundering = 1' : 'Is Laundering = 0'}
                          />
                        )}
                        {Object.keys(edge.attributes).length > 0 && (
                          <Flex direction="column" gap="1" mt="1">
                            <Text size="1" color="gray">
                              Атрибуты транзакции
                            </Text>
                            {Object.entries(edge.attributes).map(([name, value]) => (
                              <KVRow key={name} label={name} value={formatAttribute(value)} />
                            ))}
                          </Flex>
                        )}
                      </Flex>
                    )}
                  </Flex>
                </Box>
              )
            })}

            {relatedEdges.length > 12 && (
              <Text size="1" color="gray">
                +{relatedEdges.length - 12} ещё
              </Text>
            )}
          </Section>

          {neighbors.length > 0 && (
            <Flex direction="column" gap="2" p="3" style={{ minWidth: 0 }}>
              <SectionLabel>Соседи ({neighbors.length})</SectionLabel>
              <Flex direction="column" gap="1">
                {neighbors.slice(0, 12).map(n => {
                  const nScore = scoreMap.get(n.id) ?? n.risk_score ?? 0
                  return (
                    <Box
                      key={n.id}
                      onClick={() => onSelectNode(n)}
                      style={{
                        cursor: 'pointer',
                        borderRadius: 'var(--radius-2)',
                        padding: '3px 6px',
                        transition: 'background 150ms',
                        minWidth: 0
                      }}
                      className="hover:bg-[var(--gray-3)]"
                    >
                      <Flex align="center" justify="between" gap="2" style={{ minWidth: 0 }}>
                        <Text
                          size="2"
                          style={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            minWidth: 0,
                            flex: 1
                          }}
                        >
                          {n.id}
                        </Text>
                        <Badge
                          color={RISK_COLOR[riskLevel(nScore)]}
                          variant="soft"
                          size="1"
                          style={{ flexShrink: 0 }}
                        >
                          {Math.round(nScore * 100)}%
                        </Badge>
                      </Flex>
                    </Box>
                  )
                })}
                {neighbors.length > 12 && (
                  <Text size="1" color="gray" ml="1">
                    +{neighbors.length - 12} ещё
                  </Text>
                )}
              </Flex>
            </Flex>
          )}
        </Box>
      </ScrollArea>
    </Flex>
  )
}

function RiskRow({ label, value, weight }: { label: string; value: number; weight: number }) {
  return (
    <Flex align="center" gap="2" style={{ minWidth: 0 }}>
      <Text size="1" color="gray" style={{ width: 110, flexShrink: 0 }}>
        {label}
      </Text>
      <Box style={{ flex: 1, minWidth: 0 }}>
        <Progress value={Math.min(value * 100, 100)} color="blue" size="1" />
      </Box>
      <Text
        size="1"
        color="gray"
        style={{ width: 32, textAlign: 'right', fontVariantNumeric: 'tabular-nums', flexShrink: 0 }}
      >
        {(value * weight).toFixed(2)}
      </Text>
    </Flex>
  )
}
