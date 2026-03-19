import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import ConnectClient from './ConnectClient'

export default async function ConnectPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; connected?: string }>
}) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  // Check if user already has a CRM connection
  const { data: connection } = await supabase
    .from('crm_connections')
    .select('*')
    .eq('user_id', user.id)
    .single()

  const { error, connected } = await searchParams

  return (
    <ConnectClient
      user={user}
      existingConnection={connection}
      oauthError={error}
      oauthSuccess={!!connected}
    />
  )
}
