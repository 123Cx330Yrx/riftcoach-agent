export function SafeMarkdown({ markdown }: { readonly markdown: string }) {
  return (
    <div className="safe-markdown">
      <p className="safe-markdown__plaintext">{markdown}</p>
    </div>
  )
}
