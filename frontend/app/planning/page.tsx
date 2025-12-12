'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { format } from 'date-fns'
import { nl } from 'date-fns/locale'
import Link from 'next/link'
import { ArrowLeft, Plus, Filter } from 'lucide-react'
import { workshopsApi, configApi, Workshop, WorkshopType, Location } from '@/lib/api'

export default function PlanningPage() {
  const [selectedWorkshop, setSelectedWorkshop] = useState<Workshop | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<{
    status?: string
    location_id?: string
    type_id?: string
  }>({})

  // Fetch workshops
  const { data: workshops, isLoading } = useQuery({
    queryKey: ['workshops', filters],
    queryFn: () => workshopsApi.list(filters),
  })

  // Fetch config for filters
  const { data: locations } = useQuery({
    queryKey: ['locations'],
    queryFn: () => configApi.locations.list(),
  })

  const { data: workshopTypes } = useQuery({
    queryKey: ['workshopTypes'],
    queryFn: () => configApi.workshopTypes.list(),
  })

  // Convert workshops to calendar events
  const events = workshops?.map((ws) => ({
    id: ws.id,
    title: `${ws.display_code} (${ws.current_participants}/${ws.type.name})`,
    start: ws.start_date,
    end: ws.end_date || ws.start_date,
    className: `workshop-${ws.type.code}`,
    extendedProps: ws,
  })) || []

  const handleEventClick = (info: { event: { extendedProps: Workshop } }) => {
    setSelectedWorkshop(info.event.extendedProps)
  }

  const handleDateSelect = (selectInfo: { startStr: string; endStr: string }) => {
    // Could open a "create workshop" modal here
    console.log('Selected dates:', selectInfo.startStr, selectInfo.endStr)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Link href="/" className="mr-4 text-gray-500 hover:text-gray-700">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">Planning</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
              </button>
              <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700">
                <Plus className="h-4 w-4 mr-2" />
                Nieuwe workshop
              </button>
            </div>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
              <select
                value={filters.status || ''}
                onChange={(e) => setFilters({ ...filters, status: e.target.value || undefined })}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              >
                <option value="">Alle statussen</option>
                <option value="DRAFT">Concept</option>
                <option value="PUBLISHED">Gepubliceerd</option>
                <option value="CONFIRMED">Bevestigd</option>
                <option value="CANCELLED">Geannuleerd</option>
              </select>

              <select
                value={filters.location_id || ''}
                onChange={(e) => setFilters({ ...filters, location_id: e.target.value || undefined })}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              >
                <option value="">Alle locaties</option>
                {locations?.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>

              <select
                value={filters.type_id || ''}
                onChange={(e) => setFilters({ ...filters, type_id: e.target.value || undefined })}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              >
                <option value="">Alle types</option>
                {workshopTypes?.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.code} - {type.name}
                  </option>
                ))}
              </select>

              <button
                onClick={() => setFilters({})}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Filters wissen
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Calendar */}
          <div className="lg:col-span-3 bg-white rounded-lg shadow-sm p-4">
            {isLoading ? (
              <div className="h-[600px] flex items-center justify-center">
                <p className="text-gray-500">Laden...</p>
              </div>
            ) : (
              <FullCalendar
                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                initialView="dayGridMonth"
                headerToolbar={{
                  left: 'prev,next today',
                  center: 'title',
                  right: 'dayGridMonth,timeGridWeek',
                }}
                locale="nl"
                events={events}
                eventClick={handleEventClick}
                selectable={true}
                select={handleDateSelect}
                height={600}
                eventClassNames={(arg) => {
                  const typeCode = arg.event.extendedProps?.type?.code
                  return typeCode ? [`workshop-${typeCode}`] : []
                }}
              />
            )}
          </div>

          {/* Sidebar - Workshop details */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Workshop details
            </h2>

            {selectedWorkshop ? (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500">Code</p>
                  <p className="font-medium">{selectedWorkshop.display_code}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Type</p>
                  <p className="font-medium">{selectedWorkshop.type.name}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Locatie</p>
                  <p className="font-medium">{selectedWorkshop.location.name}</p>
                  <p className="text-sm text-gray-500">{selectedWorkshop.location.address}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Datum</p>
                  <p className="font-medium">
                    {format(new Date(selectedWorkshop.start_date), 'PPP', { locale: nl })}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      selectedWorkshop.status === 'CONFIRMED'
                        ? 'bg-green-100 text-green-800'
                        : selectedWorkshop.status === 'PUBLISHED'
                        ? 'bg-blue-100 text-blue-800'
                        : selectedWorkshop.status === 'CANCELLED'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {selectedWorkshop.status}
                  </span>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Deelnemers</p>
                  <p className="font-medium">{selectedWorkshop.current_participants}</p>
                </div>

                <div className="pt-4 border-t space-y-2">
                  <button className="w-full px-4 py-2 text-sm font-medium text-primary-600 border border-primary-600 rounded-md hover:bg-primary-50">
                    Bewerken
                  </button>
                  <button className="w-full px-4 py-2 text-sm font-medium text-red-600 border border-red-600 rounded-md hover:bg-red-50">
                    Annuleren
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">
                Selecteer een workshop in de kalender om details te zien.
              </p>
            )}

            {/* Legend */}
            <div className="mt-8 pt-4 border-t">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Legenda</h3>
              <div className="space-y-1">
                {workshopTypes?.map((type) => (
                  <div key={type.id} className="flex items-center">
                    <div
                      className={`w-3 h-3 rounded mr-2 bg-workshop-${type.code}`}
                      style={{
                        backgroundColor:
                          type.code === 'BWS'
                            ? '#3b82f6'
                            : type.code === 'BTC'
                            ? '#8b5cf6'
                            : type.code === 'VWS'
                            ? '#10b981'
                            : type.code === 'IWS'
                            ? '#f59e0b'
                            : type.code === 'AWS'
                            ? '#ef4444'
                            : '#ec4899',
                      }}
                    />
                    <span className="text-sm text-gray-600">
                      {type.code} - {type.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
