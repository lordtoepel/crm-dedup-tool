'use client'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-200 rounded ${className}`}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow p-4 border-2 border-transparent">
      <div className="flex items-start gap-4">
        <Skeleton className="w-5 h-5 rounded" />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <Skeleton className="w-20 h-6 rounded-full" />
              <Skeleton className="w-16 h-4" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="w-16 h-4" />
              <Skeleton className="w-16 h-4" />
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Skeleton className="w-8 h-8 rounded-full" />
              <div>
                <Skeleton className="w-32 h-4 mb-1" />
                <Skeleton className="w-40 h-3" />
              </div>
            </div>
            <Skeleton className="w-4 h-4" />
            <div className="flex items-center gap-2">
              <Skeleton className="w-8 h-8 rounded-full" />
              <div>
                <Skeleton className="w-28 h-4 mb-1" />
                <Skeleton className="w-36 h-3" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function DuplicateListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-gray-50 rounded-lg p-3">
        <Skeleton className="w-20 h-3 mb-2" />
        <Skeleton className="w-16 h-8" />
      </div>
      <div className="bg-gray-50 rounded-lg p-3">
        <Skeleton className="w-24 h-3 mb-2" />
        <Skeleton className="w-12 h-8" />
      </div>
    </div>
  )
}

export function ReportCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <Skeleton className="w-48 h-5 mb-2" />
          <Skeleton className="w-32 h-4" />
        </div>
        <Skeleton className="w-32 h-10 rounded-lg" />
      </div>
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="text-center">
            <Skeleton className="w-16 h-8 mx-auto mb-1" />
            <Skeleton className="w-20 h-3 mx-auto" />
          </div>
        ))}
      </div>
    </div>
  )
}
