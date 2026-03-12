'use client'

interface Contact {
  id?: string
  email?: string
  first_name?: string
  last_name?: string
  full_name?: string
  phone?: string
  company?: string
  job_title?: string
  created_at?: string
  updated_at?: string
  association_count?: number
  raw_properties?: Record<string, unknown>
}

interface DuplicateSet {
  id: string
  confidence: number
  winner_record_id: string
  loser_record_ids: string[]
  winner_data: Contact
  loser_data: Contact[]
  merged_preview: Record<string, unknown>
  excluded: boolean
  merged: boolean
}

interface DuplicateDetailProps {
  duplicateSet: DuplicateSet
  onClose: () => void
}

function getContactName(contact: Contact): string {
  if (contact.full_name) return contact.full_name
  const parts = [contact.first_name, contact.last_name].filter(Boolean)
  return parts.join(' ') || 'Unknown'
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return 'N/A'
  try {
    return new Date(dateStr).toLocaleDateString()
  } catch {
    return 'N/A'
  }
}

const DISPLAY_FIELDS: { key: keyof Contact | string; label: string }[] = [
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'company', label: 'Company' },
  { key: 'job_title', label: 'Job Title' },
  { key: 'created_at', label: 'Created' },
  { key: 'updated_at', label: 'Updated' },
  { key: 'association_count', label: 'Associations' },
]

export default function DuplicateDetail({
  duplicateSet,
  onClose,
}: DuplicateDetailProps) {
  const winner = duplicateSet.winner_data
  const losers = duplicateSet.loser_data
  const allContacts = [winner, ...losers]

  const getValue = (contact: Contact, key: string): string => {
    if (key === 'created_at' || key === 'updated_at') {
      return formatDate(contact[key as keyof Contact] as string)
    }
    const value = contact[key as keyof Contact]
    if (value === undefined || value === null) return '-'
    return String(value)
  }

  const getMergedValue = (key: string): string => {
    const value = duplicateSet.merged_preview[key]
    if (value === undefined || value === null) return '-'
    if (key === 'created_at' || key === 'updated_at') {
      return formatDate(value as string)
    }
    return String(value)
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative min-h-screen flex items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Duplicate Set Details
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {allContacts.length} records with {duplicateSet.confidence.toFixed(0)}% match confidence
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
            {/* Side-by-Side Comparison */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-500 w-32">
                      Field
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-green-600 bg-green-50">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 bg-green-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                          W
                        </span>
                        {getContactName(winner)}
                        <span className="text-xs text-green-500">(Winner)</span>
                      </div>
                    </th>
                    {losers.map((loser, idx) => (
                      <th key={idx} className="text-left py-3 px-4 text-sm font-medium text-gray-600 bg-gray-50">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 bg-gray-400 text-white rounded-full flex items-center justify-center text-xs font-bold">
                            L
                          </span>
                          {getContactName(loser)}
                        </div>
                      </th>
                    ))}
                    <th className="text-left py-3 px-4 text-sm font-medium text-blue-600 bg-blue-50">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                          M
                        </span>
                        Merged Result
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {DISPLAY_FIELDS.map(({ key, label }) => (
                    <tr key={key} className="border-b">
                      <td className="py-3 px-4 text-sm font-medium text-gray-500">
                        {label}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-900 bg-green-50">
                        {getValue(winner, key)}
                      </td>
                      {losers.map((loser, idx) => {
                        const winnerVal = getValue(winner, key)
                        const loserVal = getValue(loser, key)
                        const isDifferent = winnerVal !== loserVal && loserVal !== '-'
                        return (
                          <td
                            key={idx}
                            className={`py-3 px-4 text-sm bg-gray-50 ${
                              isDifferent ? 'text-orange-600' : 'text-gray-900'
                            }`}
                          >
                            {loserVal}
                            {isDifferent && loserVal !== '-' && winnerVal === '-' && (
                              <span className="ml-2 text-xs text-green-600">(will fill)</span>
                            )}
                          </td>
                        )
                      })}
                      <td className="py-3 px-4 text-sm text-gray-900 bg-blue-50 font-medium">
                        {getMergedValue(key)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Legend */}
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Merge Strategy</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                  Winner&apos;s field values take precedence
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-orange-500 rounded-full"></span>
                  Different values highlighted - blank winner fields filled from losers
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                  Final merged result after combining
                </li>
              </ul>
            </div>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-white border-t px-6 py-4 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
