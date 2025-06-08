'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Cookies from 'js-cookie';
import Layout from '@/components/Layout';
import { slotsAPI, providersAPI, patientsAPI } from '@/lib/api';
import { Slot, Provider, Patient, SlotFormData } from '@/types';
import { Trash2, Plus, Calendar, Clock, User, Search } from 'lucide-react';

export default function SlotsPage() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [eligiblePatients, setEligiblePatients] = useState<Patient[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SlotFormData>();

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
      const [slotsData, providersData] = await Promise.all([
        slotsAPI.getAll(),
        providersAPI.getAll(),
      ]);
      
      setSlots(slotsData);
      setProviders(providersData);
    } catch (err: any) {
      setError('Failed to load data');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data: SlotFormData) => {
    setSubmitting(true);
    setError('');

    try {
      // Calculate slot_period from slot_time
      const timeObj = new Date(`2000-01-01T${data.slot_time}`);
      const slot_period = timeObj.getHours() >= 12 ? 'PM' : 'AM';

      const formData = {
        ...data,
        slot_period,
      };

      await slotsAPI.add(formData);
      reset();
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add slot');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemoveSlot = async (slot: Slot) => {
    if (confirm(`Are you sure you want to remove this slot for ${slot.provider} on ${slot.slot_date}?`)) {
      try {
        await slotsAPI.remove(slot.id);
        setSlots(slots.filter(s => s.id !== slot.id));
      } catch (err: any) {
        setError('Failed to remove slot');
      }
    }
  };

  const handleFindMatches = async (slot: Slot) => {
    setSelectedSlot(slot);
    setLoadingMatches(true);
    setEligiblePatients([]);

    try {
      // For now, we'll get all patients since we don't have a findMatchesForSlot endpoint
      const response = await patientsAPI.getAll();
      setEligiblePatients(response || []);
    } catch (err: any) {
      setError('Failed to find matching patients');
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleProposeSlot = async (slotId: string, patientId: string) => {
    try {
      await slotsAPI.proposeSlot(slotId, patientId);
      loadData(); // Refresh slots to update status
      setSelectedSlot(null);
      setEligiblePatients([]);
    } catch (err: any) {
      setError('Failed to propose slot');
    }
  };

  const handleConfirmBooking = async (slotId: string, patientId: string) => {
    try {
      await slotsAPI.confirmBooking(slotId, patientId);
      loadData(); // Refresh slots
    } catch (err: any) {
      setError('Failed to confirm booking');
    }
  };

  const handleCancelProposal = async (slotId: string, patientId: string) => {
    try {
      await slotsAPI.cancelProposal(slotId, patientId);
      loadData(); // Refresh slots
    } catch (err: any) {
      setError('Failed to cancel proposal');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'available': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const formatTime = (timeStr: string) => {
    const time = new Date(`2000-01-01T${timeStr}`);
    return time.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  if (loading) {
    return (
      <Layout title="Open Slots">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">Loading...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Open Slots">
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
          page before adding slots.
        </div>
      )}

      <div className="space-y-8">
        {/* Add Slot Form */}
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Plus className="w-5 h-5 mr-2" />
            Add New Open Slot
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label htmlFor="provider" className="block text-sm font-medium text-gray-700 mb-1">
                  Provider *
                </label>
                <select
                  id="provider"
                  {...register('provider', { required: 'Provider is required' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Provider</option>
                  {providers.map(provider => (
                    <option key={provider.id} value={provider.name}>
                      {provider.name}
                    </option>
                  ))}
                </select>
                {errors.provider && (
                  <p className="text-red-500 text-sm mt-1">{errors.provider.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="slot_date" className="block text-sm font-medium text-gray-700 mb-1">
                  Date *
                </label>
                <input
                  type="date"
                  id="slot_date"
                  {...register('slot_date', { required: 'Date is required' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.slot_date && (
                  <p className="text-red-500 text-sm mt-1">{errors.slot_date.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="slot_time" className="block text-sm font-medium text-gray-700 mb-1">
                  Time *
                </label>
                <input
                  type="time"
                  id="slot_time"
                  {...register('slot_time', { required: 'Time is required' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.slot_time && (
                  <p className="text-red-500 text-sm mt-1">{errors.slot_time.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="duration" className="block text-sm font-medium text-gray-700 mb-1">
                  Duration (min) *
                </label>
                <input
                  type="number"
                  id="duration"
                  defaultValue={30}
                  {...register('duration', { 
                    required: 'Duration is required',
                    valueAsNumber: true,
                    min: { value: 15, message: 'Minimum 15 minutes' }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.duration && (
                  <p className="text-red-500 text-sm mt-1">{errors.duration.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
                Notes
              </label>
              <textarea
                id="notes"
                rows={2}
                {...register('notes')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional notes about this slot"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || providers.length === 0}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {submitting ? 'Adding Slot...' : 'Add Open Slot'}
            </button>
          </form>
        </div>

        {/* Slots List */}
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold">
              Open Slots ({slots.length})
            </h2>
          </div>

          {slots.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              <p>No open slots available.</p>
              <p className="text-sm mt-2">Add cancelled appointment slots using the form above.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {slots.map((slot) => (
                <div key={slot.id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-4 mb-2">
                        <div className="flex items-center">
                          <Calendar className="w-4 h-4 mr-1 text-gray-500" />
                          <span className="font-medium">{formatDate(slot.slot_date)}</span>
                        </div>
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 mr-1 text-gray-500" />
                          <span>{formatTime(slot.slot_time)} ({slot.duration} min)</span>
                        </div>
                        <div className="flex items-center">
                          <User className="w-4 h-4 mr-1 text-gray-500" />
                          <span>{slot.provider}</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-4">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(slot.status)}`}>
                          {slot.status || 'Available'}
                        </span>
                        
                        {slot.status?.toLowerCase() === 'pending' && slot.proposed_patient_name && (
                          <span className="text-sm text-blue-600">
                            Proposed to: {slot.proposed_patient_name}
                          </span>
                        )}
                        
                        {slot.notes && (
                          <span className="text-sm text-gray-500">
                            Note: {slot.notes}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {slot.status?.toLowerCase() === 'available' && (
                        <button
                          onClick={() => handleFindMatches(slot)}
                          className="text-blue-600 hover:text-blue-900 p-2"
                          title="Find matching patients"
                        >
                          <Search className="w-4 h-4" />
                        </button>
                      )}
                      
                      {slot.status?.toLowerCase() === 'pending' && (
                        <>
                          <button
                            onClick={() => handleConfirmBooking(slot.id, slot.proposed_patient_id!)}
                            className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => handleCancelProposal(slot.id, slot.proposed_patient_id!)}
                            className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                      
                      <button
                        onClick={() => handleRemoveSlot(slot)}
                        className="text-red-600 hover:text-red-900 p-2"
                        title="Remove slot"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Matching Patients Modal */}
      {selectedSlot && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">
                Matching Patients for {selectedSlot.provider} on {formatDate(selectedSlot.slot_date)}
              </h3>
            </div>
            
            <div className="p-6">
              {loadingMatches ? (
                <div className="text-center py-8">Loading matching patients...</div>
              ) : eligiblePatients.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No eligible patients found for this slot.
                </div>
              ) : (
                <div className="space-y-4">
                  {eligiblePatients.map((patient) => (
                    <div key={patient.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="font-medium text-lg">{patient.name}</h4>
                          <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-gray-500">Phone:</span> {patient.phone}
                            </div>
                            <div>
                              <span className="text-gray-500">Urgency:</span> {patient.urgency}
                            </div>
                            <div>
                              <span className="text-gray-500">Duration:</span> {patient.duration} min
                            </div>
                            <div>
                              <span className="text-gray-500">Wait Time:</span> {patient.wait_time}
                            </div>
                          </div>
                          {patient.reason && (
                            <div className="mt-2">
                              <span className="text-gray-500">Reason:</span> {patient.reason}
                            </div>
                          )}
                        </div>
                        
                        <button
                          onClick={() => handleProposeSlot(selectedSlot.id, patient.id)}
                          className="ml-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Propose Slot
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => {
                  setSelectedSlot(null);
                  setEligiblePatients([]);
                }}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
} 