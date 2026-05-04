import { CockpitShell } from '@/components/CockpitShell'

interface PageProps {
  params: Promise<{
    owner: string
    repo: string
    pr_number: string
  }>
}

export default async function CockpitPage({ params }: PageProps) {
  const { owner, repo, pr_number } = await params
  const prRef = {
    owner,
    repo,
    pr_number: parseInt(pr_number, 10),
    raw_url: `https://github.com/${owner}/${repo}/pull/${pr_number}`,
  }
  return <CockpitShell prRef={prRef} />
}
