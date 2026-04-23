/**
 * Component tests for FileTabBar.
 *
 * Verifies: last file has no close button (prevents empty state), multi-file
 * close, and that the add button is hidden at MAX_TABS.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileTabBar } from '../components/FileTabBar';

const makeFiles = (...names: string[]): Record<string, string> =>
  Object.fromEntries(names.map((n) => [n, `# ${n}`]));

describe('FileTabBar — single file', () => {
  it('renders the file name', () => {
    render(
      <FileTabBar
        files={makeFiles('main.py')}
        activeFile="main.py"
        onSelectFile={vi.fn()}
        onAddFile={vi.fn()}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(screen.getByText('main.py')).toBeInTheDocument();
  });

  it('does NOT render a close button when only one file exists', () => {
    render(
      <FileTabBar
        files={makeFiles('main.py')}
        activeFile="main.py"
        onSelectFile={vi.fn()}
        onAddFile={vi.fn()}
        onRemoveFile={vi.fn()}
      />,
    );
    // The close button has title="Close main.py"
    expect(screen.queryByTitle('Close main.py')).toBeNull();
  });

  it('shows add button when below MAX_TABS', () => {
    render(
      <FileTabBar
        files={makeFiles('main.py')}
        activeFile="main.py"
        onSelectFile={vi.fn()}
        onAddFile={vi.fn()}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(screen.getByTitle(/add new file/i)).toBeInTheDocument();
  });
});

describe('FileTabBar — multiple files', () => {
  it('renders close buttons for each file when multiple exist', () => {
    render(
      <FileTabBar
        files={makeFiles('a.py', 'b.py')}
        activeFile="a.py"
        onSelectFile={vi.fn()}
        onAddFile={vi.fn()}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(screen.getByTitle('Close a.py')).toBeInTheDocument();
    expect(screen.getByTitle('Close b.py')).toBeInTheDocument();
  });

  it('calls onRemoveFile with the correct name when close is clicked', async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    render(
      <FileTabBar
        files={makeFiles('a.py', 'b.py')}
        activeFile="a.py"
        onSelectFile={vi.fn()}
        onAddFile={vi.fn()}
        onRemoveFile={onRemove}
      />,
    );
    await user.click(screen.getByTitle('Close b.py'));
    expect(onRemove).toHaveBeenCalledWith('b.py');
  });

  it('calls onSelectFile when a tab is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <FileTabBar
        files={makeFiles('a.py', 'b.py')}
        activeFile="a.py"
        onSelectFile={onSelect}
        onAddFile={vi.fn()}
        onRemoveFile={vi.fn()}
      />,
    );
    await user.click(screen.getByText('b.py'));
    expect(onSelect).toHaveBeenCalledWith('b.py');
  });
});

describe('FileTabBar — MAX_TABS limit', () => {
  it('hides add button at exactly MAX_TABS (5) files', () => {
    render(
      <FileTabBar
        files={makeFiles('a.py', 'b.py', 'c.py', 'd.py', 'e.py')}
        activeFile="a.py"
        onSelectFile={vi.fn()}
        onAddFile={vi.fn()}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(screen.queryByTitle(/add new file/i)).toBeNull();
  });
});
