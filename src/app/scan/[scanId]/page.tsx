import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import ScanProgressClient from './ScanProgressClient'

interface ScanPageProps {
  params: Promise<{ scanId: string }>
}

export default async function ScanProgressPage({ params }: ScanPageProps) {
  const { scanId } = await params
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  // Get scan details
  const { data: scan, error } = await supabase
    .from('scans')
    .select('*')
    .eq('id', scanId)
    .eq('user_id', user.id)
    .single()

  if (error || !scan) {
    redirect('/scan')
  }

  // If scan is completed, redirect to review
  if (scan.status === 'completed') {
    redirect(`/review/${scanId}`)
  }

  return <ScanProgressClient scan={scan} />
}
