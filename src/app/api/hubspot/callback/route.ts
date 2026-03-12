import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  if (!code) {
    return NextResponse.redirect(`${origin}/connect?error=no_code`)
  }

  // Get current user
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return NextResponse.redirect(`${origin}/login`)
  }

  try {
    // Exchange code for tokens via our Python backend
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await fetch(`${apiUrl}/hubspot/exchange-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code,
        redirect_uri: `${origin}/api/hubspot/callback`,
        user_id: user.id,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      console.error('Token exchange failed:', error)
      return NextResponse.redirect(`${origin}/connect?error=token_exchange_failed`)
    }

    // Success - redirect to connect page
    return NextResponse.redirect(`${origin}/connect?connected=true`)
  } catch (error) {
    console.error('HubSpot callback error:', error)
    return NextResponse.redirect(`${origin}/connect?error=connection_failed`)
  }
}
