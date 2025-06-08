'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import { authAPI } from '@/lib/api';
import { User } from '@/types';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

export default function Layout({ children, title = 'Waitlist Management System' }: LayoutProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = Cookies.get('access_token');
    if (token) {
      // In a real app, you would decode the JWT or make an API call to get user info
      setUser({ id: '1', username: 'user' }); // Placeholder
    }
    setLoading(false);
  }, []);

  const handleLogout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
      router.push('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-blue-600 text-white shadow-lg">
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="text-xl font-bold">
              Waitlist Manager
            </Link>
            
            <div className="flex items-center space-x-4">
              {user ? (
                <>
                  <Link 
                    href="/" 
                    className="hover:bg-blue-700 px-3 py-2 rounded transition-colors"
                  >
                    Dashboard
                  </Link>
                  <Link 
                    href="/slots" 
                    className="hover:bg-blue-700 px-3 py-2 rounded transition-colors"
                  >
                    Slots
                  </Link>
                  <Link 
                    href="/providers" 
                    className="hover:bg-blue-700 px-3 py-2 rounded transition-colors"
                  >
                    Providers
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="bg-blue-700 hover:bg-blue-800 px-3 py-2 rounded transition-colors"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link 
                    href="/login" 
                    className="hover:bg-blue-700 px-3 py-2 rounded transition-colors"
                  >
                    Login
                  </Link>
                  <Link 
                    href="/register" 
                    className="hover:bg-blue-700 px-3 py-2 rounded transition-colors"
                  >
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto">
          {title && title !== 'Waitlist Management System' && (
            <h1 className="text-3xl font-bold text-gray-900 mb-8">{title}</h1>
          )}
          {children}
        </div>
      </main>
    </div>
  );
} 