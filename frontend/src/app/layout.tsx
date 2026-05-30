import type { Metadata } from 'next'
import { Theme } from '@radix-ui/themes'
import './globals.css'

export const metadata: Metadata = {
  title: 'AML Graph Visualizer',
  description: 'AML transaction graph investigation UI'
}

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ru" className="h-full antialiased">
      <body className="flex flex-col">
        <Theme appearance="dark" accentColor="blue" grayColor="auto" radius="medium">
          {children}
        </Theme>
      </body>
    </html>
  )
}
