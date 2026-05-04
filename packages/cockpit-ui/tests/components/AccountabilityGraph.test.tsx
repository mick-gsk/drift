import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ClusterNode } from '@/components/AccountabilityGraph/ClusterNode'
import { ClusterFileList } from '@/components/AccountabilityGraph/ClusterFileList'
import type { AccountabilityCluster, ClusterFile } from '@/types/cockpit'

const DOMINANT_CLUSTER: AccountabilityCluster = {
  cluster_id: 'c1',
  label: 'Auth Module',
  risk_share: 0.6,
  dominant: true,
  files: [
    { path: 'src/auth.py', contribution: 0.7 },
    { path: 'src/session.py', contribution: 0.3 },
  ],
}

const NORMAL_CLUSTER: AccountabilityCluster = {
  cluster_id: 'c2',
  label: 'Config',
  risk_share: 0.4,
  dominant: false,
  files: [{ path: 'src/config.py', contribution: 1.0 }],
}

// ---------------------------------------------------------------------------
// ClusterNode
// ---------------------------------------------------------------------------
describe('ClusterNode', () => {
  it('renders cluster label and risk share', () => {
    render(
      <ClusterNode
        cluster={DOMINANT_CLUSTER}
        expanded={false}
        onToggle={vi.fn()}
      />,
    )
    expect(screen.getByTestId('cluster-node')).toBeInTheDocument()
    expect(screen.getByTestId('cluster-node')).toHaveTextContent('Auth Module')
    expect(screen.getByTestId('cluster-node')).toHaveTextContent('60%')
  })

  it('highlights dominant cluster', () => {
    render(
      <ClusterNode
        cluster={DOMINANT_CLUSTER}
        expanded={false}
        onToggle={vi.fn()}
      />,
    )
    expect(screen.getByText('Dominant')).toBeInTheDocument()
  })

  it('does not highlight non-dominant cluster', () => {
    render(
      <ClusterNode
        cluster={NORMAL_CLUSTER}
        expanded={false}
        onToggle={vi.fn()}
      />,
    )
    expect(screen.queryByText('Dominant')).not.toBeInTheDocument()
  })

  it('calls onToggle on click', () => {
    const onToggle = vi.fn()
    render(
      <ClusterNode
        cluster={NORMAL_CLUSTER}
        expanded={false}
        onToggle={onToggle}
      />,
    )
    fireEvent.click(screen.getByTestId('cluster-node'))
    expect(onToggle).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// ClusterFileList
// ---------------------------------------------------------------------------
describe('ClusterFileList', () => {
  const files: ClusterFile[] = [
    { path: 'src/a.py', contribution: 0.6 },
    { path: 'src/b.py', contribution: 0.4 },
  ]

  it('renders all file items', () => {
    render(<ClusterFileList files={files} />)
    expect(screen.getAllByTestId('cluster-file-item')).toHaveLength(2)
  })

  it('shows contribution percentages', () => {
    render(<ClusterFileList files={files} />)
    expect(screen.getByText('60%')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
  })
})
