import type { Metadata } from 'next'
import './globals.css'
import { GlobalErrorBoundary } from '@/components/GlobalErrorBoundary'

export const metadata: Metadata = {
  title: 'Drift Cockpit',
  description: 'PR merge governance dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <GlobalErrorBoundary>{children}</GlobalErrorBoundary>
      </body>
    </html>
  )
}
