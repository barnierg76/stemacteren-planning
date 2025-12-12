import Link from 'next/link'
import { Calendar, Users, MessageSquare, Settings, BarChart3 } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              Stemacteren Planning
            </h1>
            <nav className="flex space-x-4">
              <Link
                href="/planning"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Planning
              </Link>
              <Link
                href="/chat"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                AI Chat
              </Link>
              <Link
                href="/team"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Team
              </Link>
              <Link
                href="/config"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Instellingen
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Welkom bij het planningsysteem
          </h2>
          <p className="text-gray-600">
            AI-gestuurde workshop planning voor Stemacteren.nl
          </p>
        </div>

        {/* Quick actions grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Planning */}
          <Link
            href="/planning"
            className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 rounded-full bg-blue-100">
                <Calendar className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="ml-4 text-lg font-semibold text-gray-900">
                Planning
              </h3>
            </div>
            <p className="text-gray-600">
              Bekijk en beheer de workshop kalender
            </p>
          </Link>

          {/* AI Chat */}
          <Link
            href="/chat"
            className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 rounded-full bg-purple-100">
                <MessageSquare className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="ml-4 text-lg font-semibold text-gray-900">
                AI Assistent
              </h3>
            </div>
            <p className="text-gray-600">
              Stel vragen en geef opdrachten in natuurlijke taal
            </p>
          </Link>

          {/* Team */}
          <Link
            href="/team"
            className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 rounded-full bg-green-100">
                <Users className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="ml-4 text-lg font-semibold text-gray-900">
                Team
              </h3>
            </div>
            <p className="text-gray-600">
              Beheer docenten, technici en beschikbaarheid
            </p>
          </Link>

          {/* Reports */}
          <Link
            href="/reports"
            className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 rounded-full bg-amber-100">
                <BarChart3 className="h-6 w-6 text-amber-600" />
              </div>
              <h3 className="ml-4 text-lg font-semibold text-gray-900">
                Rapportages
              </h3>
            </div>
            <p className="text-gray-600">
              Omzet, bezetting en target voortgang
            </p>
          </Link>

          {/* Settings */}
          <Link
            href="/config"
            className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center mb-4">
              <div className="p-3 rounded-full bg-gray-100">
                <Settings className="h-6 w-6 text-gray-600" />
              </div>
              <h3 className="ml-4 text-lg font-semibold text-gray-900">
                Instellingen
              </h3>
            </div>
            <p className="text-gray-600">
              Configureer workshoptypes, locaties en regels
            </p>
          </Link>
        </div>

        {/* Stats overview (placeholder) */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow-sm p-4">
            <p className="text-sm text-gray-500">Geplande workshops</p>
            <p className="text-2xl font-bold text-gray-900">-</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <p className="text-sm text-gray-500">Deze maand</p>
            <p className="text-2xl font-bold text-gray-900">-</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <p className="text-sm text-gray-500">Verwachte omzet</p>
            <p className="text-2xl font-bold text-gray-900">-</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-4">
            <p className="text-sm text-gray-500">Nog te bevestigen</p>
            <p className="text-2xl font-bold text-gray-900">-</p>
          </div>
        </div>
      </main>
    </div>
  )
}
