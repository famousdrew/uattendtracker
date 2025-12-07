'use client'

import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider, useAuth, PasswordPrompt } from '@/lib/auth'
import Providers from '@/components/Providers'
import Navigation from '@/components/Navigation'
import { useEffect } from 'react'
import { apiClient } from '@/lib/api'

const inter = Inter({ subsets: ['latin'] })

function AppContent({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, password } = useAuth()

  useEffect(() => {
    if (password) {
      apiClient.setPassword(password)
    }
  }, [password])

  if (!isAuthenticated) {
    return <PasswordPrompt />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <title>Product Issue Miner</title>
        <meta name="description" content="Dashboard for mining and analyzing product issues" />
      </head>
      <body className={inter.className}>
        <AuthProvider>
          <Providers>
            <AppContent>{children}</AppContent>
          </Providers>
        </AuthProvider>
      </body>
    </html>
  )
}
