import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen bg-base flex items-center justify-center p-4 bg-grid-faint bg-grid">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-ai-dim border border-ai/30 mb-4">
            <span className="text-ai font-mono font-bold text-lg">S</span>
          </div>
          <h1 className="text-xl font-semibold text-ink">Join SignalStack</h1>
          <p className="text-sm text-ink-muted mt-1">Start your research workspace</p>
        </div>
        <SignUp routing="hash" />
      </div>
    </div>
  );
}