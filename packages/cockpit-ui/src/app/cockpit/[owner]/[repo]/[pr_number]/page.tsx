import { CockpitShell } from '@/components/CockpitShell'

interface PageProps {
  params: {
    owner: string
    repo: string
    pr_number: string
  }
}

export default function CockpitPage({ params }: PageProps) {
  const { owner, repo, pr_number } = params
  const prRef = {
    owner,
    repo,
    pr_number: parseInt(pr_number, 10),
    raw_url: `https://github.com/${owner}/${repo}/pull/${pr_number}`,
  }
  return <CockpitShell prRef={prRef} />
}
