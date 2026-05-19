import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-base flex items-center justify-center p-4 bg-grid-faint bg-grid">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-ai-dim border border-ai/30 mb-4">
            <span className="text-ai font-mono font-bold text-lg">S</span>
          </div>
          <h1 className="text-xl font-semibold text-ink">SignalStack</h1>
          <p className="text-sm text-ink-muted mt-1">AI-powered investment research</p>
        </div>
        <SignIn routing="hash" />
      </div>
    </div>
  );
}