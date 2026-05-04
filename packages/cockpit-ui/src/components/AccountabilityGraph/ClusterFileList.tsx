import type { ClusterFile } from '@/types/cockpit'

interface ClusterFileListProps {
  files: ClusterFile[]
}

export function ClusterFileList({ files }: ClusterFileListProps) {
  return (
    <ul className="mt-3 space-y-1 border-t border-gray-100 pt-3">
      {files.map((f) => (
        <li
          key={f.path}
          data-testid="cluster-file-item"
          className="flex items-center justify-between text-sm"
        >
          <span className="font-mono text-gray-700 truncate max-w-xs">
            {f.path}
          </span>
          <span className="text-xs text-gray-500 ml-2 shrink-0">
            {Math.round(f.contribution * 100)}%
          </span>
        </li>
      ))}
    </ul>
  )
}
