'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { patientsAPI } from '@/lib/api';
import { PatientFormData, Provider } from '@/types';

interface PatientFormProps {
  providers: Provider[];
  onPatientAdded: () => void;
}

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function PatientForm({ providers, onPatientAdded }: PatientFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [availability, setAvailability] = useState<Record<string, string[]>>({});

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PatientFormData>();

  const handleAvailabilityChange = (day: string, period: 'AM' | 'PM', checked: boolean) => {
    setAvailability(prev => {
      const newAvail = { ...prev };
      if (!newAvail[day]) newAvail[day] = [];
      
      if (checked) {
        if (!newAvail[day].includes(period)) {
          newAvail[day] = [...newAvail[day], period];
        }
      } else {
        newAvail[day] = newAvail[day].filter(p => p !== period);
        if (newAvail[day].length === 0) {
          delete newAvail[day];
        }
      }
      
      return newAvail;
    });
  };

  const onSubmit = async (data: PatientFormData) => {
    setLoading(true);
    setError('');

    try {
      const formData = {
        ...data,
        availability,
      };

      await patientsAPI.add(formData);
      reset();
      setAvailability({});
      onPatientAdded();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add patient');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-4">Add New Patient</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Basic Information */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Name *
            </label>
            <input
              type="text"
              id="name"
              {...register('name', { required: 'Name is required' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.name && (
              <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
              Phone *
            </label>
            <input
              type="tel"
              id="phone"
              {...register('phone', { required: 'Phone is required' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.phone && (
              <p className="text-red-500 text-sm mt-1">{errors.phone.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              id="email"
              {...register('email')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Appointment Details */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label htmlFor="urgency" className="block text-sm font-medium text-gray-700 mb-1">
              Urgency
            </label>
            <select
              id="urgency"
              {...register('urgency')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div>
            <label htmlFor="duration" className="block text-sm font-medium text-gray-700 mb-1">
              Duration (min)
            </label>
            <input
              type="number"
              id="duration"
              defaultValue={30}
              {...register('duration', { valueAsNumber: true })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="provider" className="block text-sm font-medium text-gray-700 mb-1">
              Provider
            </label>
            <select
              id="provider"
              {...register('provider')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="no preference">No Preference</option>
              {providers.map(provider => (
                <option key={provider.id} value={provider.name}>
                  {provider.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="appointment_type" className="block text-sm font-medium text-gray-700 mb-1">
              Appointment Type
            </label>
            <input
              type="text"
              id="appointment_type"
              {...register('appointment_type')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional"
            />
          </div>
        </div>

        {/* Reason */}
        <div>
          <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-1">
            Reason for Visit
          </label>
          <textarea
            id="reason"
            rows={2}
            {...register('reason')}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Availability */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Availability
          </label>
          <div className="grid grid-cols-7 gap-2 mb-4">
            {days.map(day => (
              <div key={day} className="text-center">
                <div className="font-medium text-sm mb-1">{day.slice(0, 3)}</div>
                <div className="space-y-1">
                  <label className="flex items-center justify-center">
                    <input
                      type="checkbox"
                      className="mr-1"
                      onChange={(e) => handleAvailabilityChange(day, 'AM', e.target.checked)}
                    />
                    <span className="text-xs">AM</span>
                  </label>
                  <label className="flex items-center justify-center">
                    <input
                      type="checkbox"
                      className="mr-1"
                      onChange={(e) => handleAvailabilityChange(day, 'PM', e.target.checked)}
                    />
                    <span className="text-xs">PM</span>
                  </label>
                </div>
              </div>
            ))}
          </div>
          
          <div>
            <select
              {...register('availability_mode')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="available">Available only on selected times</option>
              <option value="unavailable">Unavailable on selected times</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {loading ? 'Adding Patient...' : 'Add Patient'}
        </button>
      </form>
    </div>
  );
} 