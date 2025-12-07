'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

interface AuthContextType {
  password: string | null
  setPassword: (password: string) => void
  isAuthenticated: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [password, setPasswordState] = useState<string | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    // Load password from localStorage on mount
    const stored = localStorage.getItem('dashboard-password')
    if (stored) {
      setPasswordState(stored)
    }
    setIsLoaded(true)
  }, [])

  const setPassword = (pwd: string) => {
    localStorage.setItem('dashboard-password', pwd)
    setPasswordState(pwd)
  }

  const logout = () => {
    localStorage.removeItem('dashboard-password')
    setPasswordState(null)
  }

  const isAuthenticated = !!password

  // Don't render children until we've loaded from localStorage
  if (!isLoaded) {
    return null
  }

  return (
    <AuthContext.Provider value={{ password, setPassword, isAuthenticated, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Password Prompt Component
export function PasswordPrompt() {
  const [inputPassword, setInputPassword] = useState('')
  const [error, setError] = useState('')
  const { setPassword } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!inputPassword.trim()) {
      setError('Please enter a password')
      return
    }

    // Set the password (validation will happen on first API call)
    setPassword(inputPassword)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full">
        <div className="dashboard-card">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Product Issue Miner
          </h2>
          <p className="text-gray-600 mb-6 text-center">
            Please enter the dashboard password to continue
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                id="password"
                value={inputPassword}
                onChange={(e) => setInputPassword(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter password"
                autoFocus
              />
            </div>
            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}
            <button
              type="submit"
              className="w-full btn-primary"
            >
              Access Dashboard
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
