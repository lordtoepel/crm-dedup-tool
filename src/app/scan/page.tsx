import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import ScanConfigClient from './ScanConfigClient'

export default async function ScanPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  // Check for CRM connection
  const { data: connection } = await supabase
    .from('crm_connections')
    .select('*')
    .eq('user_id', user.id)
    .single()

  if (!connection) {
    redirect('/connect')
  }

  return <ScanConfigClient userId={user.id} connection={connection} />
}
