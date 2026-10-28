import { useEffect } from "react";
import { useLocation } from "react-router";

function Section({ id, title, children }: { id?: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6 space-y-2 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="space-y-2 text-sm leading-6 text-slate-700">{children}</div>
    </section>
  );
}

export function AboutPage() {
  const { hash } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [hash]);

  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">How scoring works</h1>
        <p className="text-sm text-slate-600">
          All scores are computed by the backend. This page explains the rules; the app only displays the results.
        </p>
      </div>

      <Section title="The formula">
        <p className="rounded-md bg-slate-100 px-3 py-2 font-mono text-sm">score = 0.60 × Skills + 0.25 × Experience + 0.15 × Culture</p>
        <p>
          Each component is scored from 0 to 100. These are the default weights; the server can be configured with
          different ones, and every match shows the weights it actually used in its score breakdown.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Skills</strong>: the share of the job's required skills the candidate has. Extra skills earn nothing. A job with no required skills gives full marks.</li>
          <li><strong>Experience</strong>: 100 if the candidate meets the minimum, otherwise proportional (5 years against a 10-year minimum scores 50). A job with no minimum gives full marks.</li>
          <li><strong>Culture</strong>: the share of the job's culture keywords found among the candidate's traits.</li>
        </ul>
        <p>Terms match exactly after lowercasing and trimming: <code>public-speaking</code> and <code>public speaking</code> are different skills.</p>
      </Section>

      <Section title="When culture can't be scored">
        <p>Culture is left out, rather than scored as zero, in two cases:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>the candidate's traits are unknown, or</li>
          <li>the job lists no culture keywords.</li>
        </ul>
        <p>
          The remaining weights are then rescaled to add up to 1 (with the defaults, 70.59% skills and 29.41% experience).
          The breakdown says when this happened. A candidate whose traits are <em>known</em> but match nothing scores 0 for culture.
        </p>
      </Section>

      <Section id="tie-breaks" title="Tie-breaks">
        <p>When two matches have exactly the same score, the order is decided by, in turn:</p>
        <ol className="list-decimal space-y-1 pl-5">
          <li>higher skill coverage</li>
          <li>higher experience score</li>
          <li>availability: immediate, then 2 weeks, then unknown, then not looking</li>
          <li>lower ID</li>
        </ol>
        <p>Availability never raises a score; it only orders candidates whose scores are already equal.</p>
      </Section>

      <Section title="What isn't scored">
        <p>Candidate quirks and job taglines are shown for context only and never affect a score.</p>
      </Section>
    </>
  );
}
