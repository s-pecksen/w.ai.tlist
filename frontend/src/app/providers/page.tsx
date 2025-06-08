'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Cookies from 'js-cookie';
import Layout from '@/components/Layout';
import { providersAPI } from '@/lib/api';
import { Provider, ProviderFormData } from '@/types';
import { Trash2, Plus } from 'lucide-react';

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProviderFormData>();

  useEffect(() => {
    const token = Cookies.get('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    loadProviders();
  }, [router]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const data = await providersAPI.getAll();
      setProviders(data);
    } catch (err: any) {
      setError('Failed to load providers');
      console.error('Error loading providers:', err);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data: ProviderFormData) => {
    setSubmitting(true);
    setError('');

    try {
      await providersAPI.add(data);
      reset();
      loadProviders();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add provider');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemoveProvider = async (provider: Provider) => {
    if (confirm(`Are you sure you want to remove ${provider.name}?`)) {
      try {
        await providersAPI.remove({ 
          first_name: provider.first_name, 
          last_initial: provider.last_initial 
        });
        setProviders(providers.filter(p => p.id !== provider.id));
      } catch (err: any) {
        setError('Failed to remove provider');
      }
    }
  };

  if (loading) {
    return (
      <Layout title="Providers">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">Loading...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Providers">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="space-y-8">
        {/* Add Provider Form */}
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Plus className="w-5 h-5 mr-2" />
            Add New Provider
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2">
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-700 mb-1">
                  First Name *
                </label>
                <input
                  type="text"
                  id="first_name"
                  {...register('first_name', { required: 'First name is required' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter provider's first name"
                />
                {errors.first_name && (
                  <p className="text-red-500 text-sm mt-1">{errors.first_name.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="last_initial" className="block text-sm font-medium text-gray-700 mb-1">
                  Last Initial
                </label>
                <input
                  type="text"
                  id="last_initial"
                  maxLength={1}
                  {...register('last_initial')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="X"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {submitting ? 'Adding Provider...' : 'Add Provider'}
            </button>
          </form>
        </div>

        {/* Providers List */}
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold">
              Current Providers ({providers.length})
            </h2>
          </div>

          {providers.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              <p>No providers added yet.</p>
              <p className="text-sm mt-2">Add your first provider using the form above.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {providers.map((provider) => (
                <div key={provider.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">
                      {provider.name}
                    </h3>
                    <p className="text-sm text-gray-500">
                      Provider ID: {provider.id}
                    </p>
                  </div>
                  
                  <button
                    onClick={() => handleRemoveProvider(provider)}
                    className="text-red-600 hover:text-red-900 p-2"
                    title={`Remove ${provider.name}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info Section */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">About Providers</h3>
          <div className="text-sm text-blue-700 space-y-2">
            <p>
              • Providers are the healthcare professionals who will see patients
            </p>
            <p>
              • Patients can specify a provider preference when joining the waitlist
            </p>
            <p>
              • Open slots are associated with specific providers
            </p>
            <p>
              • You can add multiple providers and manage them here
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
} 