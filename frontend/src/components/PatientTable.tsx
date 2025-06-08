'use client';

import React, { useState } from 'react';
import { Patient } from '@/types';
import { Trash2, Edit, Clock, Phone, Mail } from 'lucide-react';

interface PatientTableProps {
  patients: Patient[];
  onPatientRemoved: (patientId: string) => void;
}

export default function PatientTable({ patients, onPatientRemoved }: PatientTableProps) {
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

  const handleRemovePatient = (patient: Patient) => {
    if (confirm(`Are you sure you want to remove ${patient.name} from the waitlist?`)) {
      onPatientRemoved(patient.id);
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'pending': return 'bg-blue-100 text-blue-800';
      case 'waiting': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatAvailability = (availability: Record<string, string[]>) => {
    if (!availability || Object.keys(availability).length === 0) {
      return 'Any time';
    }
    
    return Object.entries(availability)
      .map(([day, periods]) => `${day.slice(0, 3)}: ${periods.join(', ')}`)
      .join('; ');
  };

  if (patients.length === 0) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Patient Waitlist</h2>
        <p className="text-gray-500 text-center py-8">No patients in the waitlist</p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-md rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold">Patient Waitlist ({patients.length})</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Patient
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contact
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Appointment
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Urgency
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Wait Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Availability
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {patients.map((patient) => (
              <tr key={patient.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{patient.name}</div>
                    {patient.reason && (
                      <div className="text-sm text-gray-500" title={patient.reason}>
                        {patient.reason.length > 50 
                          ? `${patient.reason.substring(0, 50)}...` 
                          : patient.reason
                        }
                      </div>
                    )}
                  </div>
                </td>
                
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="space-y-1">
                    <div className="flex items-center text-sm text-gray-900">
                      <Phone className="w-3 h-3 mr-1" />
                      {patient.phone}
                    </div>
                    {patient.email && (
                      <div className="flex items-center text-sm text-gray-500">
                        <Mail className="w-3 h-3 mr-1" />
                        {patient.email}
                      </div>
                    )}
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="space-y-1">
                    <div className="text-sm text-gray-900">
                      {patient.appointment_type || 'Not specified'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {patient.duration} min • {patient.provider || 'Any provider'}
                    </div>
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getUrgencyColor(patient.urgency)}`}>
                    {patient.urgency || 'Medium'}
                  </span>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(patient.status)}`}>
                    {patient.status || 'Waiting'}
                  </span>
                  {patient.status?.toLowerCase() === 'pending' && patient.proposed_slot_details && (
                    <div className="text-xs text-gray-500 mt-1">
                      {patient.proposed_slot_details}
                    </div>
                  )}
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center text-sm text-gray-900">
                    <Clock className="w-3 h-3 mr-1" />
                    {patient.wait_time || '0 minutes'}
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900" title={formatAvailability(patient.availability || {})}>
                    {formatAvailability(patient.availability || {}).length > 20 
                      ? `${formatAvailability(patient.availability || {}).substring(0, 20)}...`
                      : formatAvailability(patient.availability || {})
                    }
                  </div>
                  <div className="text-xs text-gray-500">
                    Mode: {patient.availability_mode || 'available'}
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                  <button
                    onClick={() => setSelectedPatient(patient)}
                    className="text-blue-600 hover:text-blue-900"
                    title="Edit patient"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleRemovePatient(patient)}
                    className="text-red-600 hover:text-red-900"
                    title="Remove patient"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Patient Details Modal */}
      {selectedPatient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">Patient Details</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name</label>
                  <p className="text-sm text-gray-900">{selectedPatient.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Phone</label>
                  <p className="text-sm text-gray-900">{selectedPatient.phone}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <p className="text-sm text-gray-900">{selectedPatient.email || 'Not provided'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Provider</label>
                  <p className="text-sm text-gray-900">{selectedPatient.provider || 'Any provider'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Duration</label>
                  <p className="text-sm text-gray-900">{selectedPatient.duration} minutes</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Urgency</label>
                  <p className="text-sm text-gray-900">{selectedPatient.urgency}</p>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Reason</label>
                <p className="text-sm text-gray-900">{selectedPatient.reason || 'Not provided'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Availability</label>
                <p className="text-sm text-gray-900">{formatAvailability(selectedPatient.availability || {})}</p>
                <p className="text-xs text-gray-500">Mode: {selectedPatient.availability_mode}</p>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setSelectedPatient(null)}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 