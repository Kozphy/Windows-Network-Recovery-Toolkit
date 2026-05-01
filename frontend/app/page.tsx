import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <h1>Windows Network Recovery SaaS</h1>
      <p>{`Client Agent -> API -> Diagnosis Engine -> Dashboard -> Billing`}</p>
      <div className="card">
        <p>Use the links below to access the SaaS MVP pages.</p>
        <ul>
          <li>
            <Link href="/login">/login</Link>
          </li>
          <li>
            <Link href="/dashboard">/dashboard</Link>
          </li>
          <li>
            <Link href="/billing">/billing</Link>
          </li>
        </ul>
      </div>
    </main>
  );
}
