import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import ReviewClient from './ReviewClient'

interface ReviewPageProps {
  params: Promise<{ scanId: string }>
}

export default async function ReviewPage({ params }: ReviewPageProps) {
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

  // If scan is not completed, redirect back to progress
  if (scan.status !== 'completed') {
    redirect(`/scan/${scanId}`)
  }

  return <ReviewClient scan={scan} userId={user.id} />
}
