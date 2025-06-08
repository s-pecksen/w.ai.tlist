'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import Layout from '@/components/Layout';
import PatientForm from '@/components/PatientForm';
import PatientTable from '@/components/PatientTable';
import { patientsAPI, providersAPI } from '@/lib/api';
import { Patient, Provider } from '@/types';

export default function DashboardPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const token = Cookies.get('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    loadData();
  }, [router]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [patientsData, providersData] = await Promise.all([
        patientsAPI.getAll(),
        providersAPI.getAll(),
      ]);
      
      setPatients(patientsData);
      setProviders(providersData);
    } catch (err: any) {
      setError('Failed to load data');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePatientAdded = () => {
    loadData(); // Refresh the patient list
  };

  const handlePatientRemoved = async (patientId: string) => {
    try {
      await patientsAPI.remove(patientId);
      setPatients(patients.filter(p => p.id !== patientId));
    } catch (err) {
      setError('Failed to remove patient');
    }
  };

  if (loading) {
    return (
      <Layout title="Dashboard">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">Loading...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Patient Waitlist">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {providers.length === 0 && (
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
          Please add providers via the{' '}
          <a href="/providers" className="font-semibold underline">
            Providers
          </a>{' '}
          page to proceed.
        </div>
      )}

      <div className="space-y-8">
        {/* Add Patient Form */}
        <PatientForm 
          providers={providers} 
          onPatientAdded={handlePatientAdded}
        />

        {/* Patient Table */}
        <PatientTable 
          patients={patients} 
          onPatientRemoved={handlePatientRemoved}
        />
      </div>
    </Layout>
  );
}
