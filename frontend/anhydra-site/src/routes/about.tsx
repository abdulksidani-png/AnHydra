import { useState } from "react";
import { Link, createFileRoute } from "@tanstack/react-router";
import { Globe } from "lucide-react";
import settings from "@/config/settings.json";
import { BUILT_WITH, TEAM, type Member } from "@/data/team";

export const Route = createFileRoute("/about")({
  head: () => settings.routes["/about"],
  component: AboutPage,
});

function GithubMark() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true" focusable="false">
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.68.41.35.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

function LinkedinMark() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true" focusable="false">
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  );
}

function Widget({ href, label, children }: { href?: string; label: string; children: React.ReactNode }) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={label}
      className="ghost-btn mt-0 inline-flex size-11 items-center justify-center p-0"
    >
      {children}
    </a>
  );
}

// The member's GitHub profile picture, linking to their profile. Hidden if it fails to load, rather
// than showing a broken image.
function GithubAvatar({ member }: { member: Member }) {
  const [failed, setFailed] = useState(false);
  const user = member.github ? new URL(member.github).pathname.split("/")[1] : "";
  if (!user || failed) return null;
  return (
    <a href={member.github} target="_blank" rel="noopener noreferrer" className="member-avatar" title={`${member.name} on GitHub`}>
      <img
        src={`https://github.com/${encodeURIComponent(user)}.png?size=160`}
        alt={`${member.name}'s GitHub profile picture`}
        width={72}
        height={72}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </a>
  );
}

function MemberCard({ member }: { member: Member }) {
  return (
    <li className="card flex items-center justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-4">
        <h3>{member.name}</h3>
        <div className="flex flex-wrap gap-2">
          <Widget href={member.github} label={`${member.name} on GitHub`}>
            <GithubMark />
          </Widget>
          <Widget href={member.linkedin} label={`${member.name} on LinkedIn`}>
            <LinkedinMark />
          </Widget>
          <Widget href={member.website} label={`${member.name}'s website`}>
            <Globe size={20} aria-hidden="true" />
          </Widget>
        </div>
      </div>
      <GithubAvatar member={member} />
    </li>
  );
}

function AboutPage() {
  return (
    <main className="page about flex flex-col gap-12">
      <section aria-labelledby="built-with" className="flex flex-col items-center gap-4 text-center">
        <h2 id="built-with">Built with</h2>
        <ul className="m-0 flex list-none flex-wrap justify-center gap-2 p-0">
          {BUILT_WITH.map((t) => (
            <li key={t.name}>
              <a href={t.url} target="_blank" rel="noopener noreferrer" className="chip no-underline">
                {t.name}
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="about-us" className="mx-auto flex max-w-3xl flex-col gap-4 text-center">
        <h2 id="about-us">About us</h2>
        <p className="big">
          An animal smaller than a grain of sand can lose almost all its water and come back to life. We wanted to know
          which proteins make that possible.
        </p>
        <p>
          Tardigrades survive drying out with the help of a few protein families: CAHS proteins in tardigrades, and LEA
          proteins and dehydrins in plants. Finding more proteins like them could help vaccines, medicines and crops
          survive without refrigeration. AnHydra is a first-pass filter: paste a sequence, see whether it looks like one
          of the protective families, and see why.
        </p>
        <p>
          Our model scored 0.987 on the test we designed to be hard. Instead of celebrating, we went looking for the
          catch and found it: our negative examples made the task easier than it looked. We rebuilt the data and
          reported the honest number.
        </p>
      </section>

      <section aria-labelledby="team" className="flex flex-col gap-4">
        <h2 id="team">Get in touch</h2>
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-4">
          {TEAM.map((m) => (
            <MemberCard key={m.name} member={m} />
          ))}
        </ul>
        <p className="privacy-link muted small text-center">
          <Link to="/privacy">Privacy</Link>
        </p>
      </section>
    </main>
  );
}
