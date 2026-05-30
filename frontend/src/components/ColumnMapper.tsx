'use client'

import { useState } from 'react'
import { Box, Button, Flex, Heading, Select, Table, Text } from '@radix-ui/themes'
import type { ColumnMapping } from '@/types/api/column-mapping'

interface ColumnMapperProps {
  columns: string[]
  preview: string[][]
  onSubmit: (mapping: ColumnMapping) => void
  isLoading: boolean
}

const REQUIRED_FIELDS: { key: keyof ColumnMapping; label: string }[] = [
  { key: 'sender_id', label: 'Sender account' },
  { key: 'receiver_id', label: 'Receiver account' },
  { key: 'amount_paid', label: 'Amount paid' },
  { key: 'timestamp', label: 'Timestamp' }
]

const OPTIONAL_FIELDS: { key: keyof ColumnMapping; label: string }[] = [
  { key: 'sender_bank', label: 'Sender bank' },
  { key: 'receiver_bank', label: 'Receiver bank' },
  { key: 'amount_received', label: 'Amount received' },
  { key: 'payment_currency', label: 'Payment currency' },
  { key: 'receiving_currency', label: 'Receiving currency' },
  { key: 'transaction_type', label: 'Payment format / type' },
  { key: 'device_id', label: 'Device ID' },
  { key: 'ip_address', label: 'IP address' },
  { key: 'is_laundering', label: 'Is laundering label' }
]

const NONE = '__none__'

function findColumn(columns: string[], hints: string[]): string | undefined {
  const lower = columns.map(c => c.toLowerCase())
  const index = hints.map(h => lower.indexOf(h)).find(i => i !== -1)
  return index === undefined ? undefined : columns[index]
}

export default function ColumnMapper({ columns, preview, onSubmit, isLoading }: ColumnMapperProps) {
  const [mapping, setMapping] = useState<Partial<ColumnMapping>>(() => ({
    sender_id: findColumn(columns, ['sender_id', 'sender', 'from', 'source']),
    receiver_id: findColumn(columns, ['receiver_id', 'receiver', 'to', 'target', 'destination']),
    amount_paid: findColumn(columns, [
      'amount_paid',
      'amount',
      'value',
      'sum',
      'transaction_amount'
    ]),
    timestamp: findColumn(columns, ['timestamp', 'time', 'date', 'created_at', 'ts']),
    device_id: findColumn(columns, ['device_id', 'device', 'device_name']),
    ip_address: findColumn(columns, ['ip_address', 'ip', 'ip_addr']),
    sender_bank: findColumn(columns, ['sender_bank', 'from_bank', 'sending_bank']),
    receiver_bank: findColumn(columns, ['receiver_bank', 'to_bank', 'receiving_bank']),
    amount_received: findColumn(columns, ['amount_received', 'received_amount']),
    payment_currency: findColumn(columns, ['payment_currency']),
    receiving_currency: findColumn(columns, ['receiving_currency']),
    transaction_type: findColumn(columns, ['transaction_type', 'payment_type', 'payment_format']),
    is_laundering: findColumn(columns, ['is_laundering', 'laundering', 'label', 'fraud'])
  }))

  function handleChange(field: keyof ColumnMapping, value: string) {
    setMapping(prev => ({ ...prev, [field]: value === NONE || !value ? undefined : value }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const { sender_id, receiver_id, amount_paid, timestamp } = mapping
    if (!sender_id || !receiver_id || !amount_paid || !timestamp) return
    onSubmit({
      sender_id,
      receiver_id,
      amount_paid,
      timestamp,
      sender_bank: mapping.sender_bank,
      receiver_bank: mapping.receiver_bank,
      amount_received: mapping.amount_received,
      payment_currency: mapping.payment_currency,
      receiving_currency: mapping.receiving_currency,
      transaction_type: mapping.transaction_type,
      device_id: mapping.device_id,
      ip_address: mapping.ip_address,
      is_laundering: mapping.is_laundering
    })
  }

  const isValid = !!(
    mapping.sender_id &&
    mapping.receiver_id &&
    mapping.amount_paid &&
    mapping.timestamp
  )

  function renderSelect(field: keyof ColumnMapping, label: string, required = false) {
    return (
      <Flex key={field} direction="column" gap="1">
        <Text as="label" size="2" weight={required ? 'medium' : 'regular'}>
          {label} {required && <Text color="red">*</Text>}
        </Text>
        <Select.Root
          value={(mapping[field] as string | undefined) ?? NONE}
          onValueChange={v => handleChange(field, v)}
        >
          <Select.Trigger placeholder={required ? 'select column' : 'not set'} />
          <Select.Content>
            {!required && <Select.Item value={NONE}>not set</Select.Item>}
            {columns.map(col => (
              <Select.Item key={col} value={col}>
                {col}
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Root>
      </Flex>
    )
  }

  return (
    <Flex direction="column" gap="5" style={{ width: '100%' }}>
      <Flex direction="column" gap="1">
        <Heading size="4">CSV column mapping</Heading>
        <Text size="2" color="gray">
          Select which CSV columns correspond to transaction graph fields.
        </Text>
      </Flex>

      {preview.length > 0 && (
        <Box style={{ overflowX: 'auto' }}>
          <Table.Root size="1" variant="surface">
            <Table.Header>
              <Table.Row>
                {columns.map(col => (
                  <Table.ColumnHeaderCell key={col}>{col}</Table.ColumnHeaderCell>
                ))}
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {preview.map((row, ri) => (
                <Table.Row key={ri}>
                  {row.map((cell, ci) => (
                    <Table.Cell key={ci}>
                      <Text
                        size="1"
                        color="gray"
                        style={{
                          maxWidth: 120,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          display: 'block'
                        }}
                      >
                        {cell}
                      </Text>
                    </Table.Cell>
                  ))}
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        </Box>
      )}

      <form onSubmit={handleSubmit}>
        <Flex direction="column" gap="4">
          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Required
            </Text>
            <Box style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              {REQUIRED_FIELDS.map(({ key, label }) => renderSelect(key, label, true))}
            </Box>
          </Flex>

          <Flex direction="column" gap="2">
            <Text
              size="1"
              weight="medium"
              color="gray"
              style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              Optional
            </Text>
            <Box style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              {OPTIONAL_FIELDS.map(({ key, label }) => renderSelect(key, label))}
            </Box>
          </Flex>

          <Button type="submit" disabled={!isValid || isLoading} loading={isLoading} size="3">
            Analyze graph
          </Button>
        </Flex>
      </form>
    </Flex>
  )
}
