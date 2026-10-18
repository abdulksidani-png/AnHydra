export type Member = {
  name: string;
  github?: string;
  linkedin?: string;
  website?: string;
};

export const BUILT_WITH = [
  { name: "ESM-2", url: "https://github.com/facebookresearch/esm" },
  { name: "PyTorch", url: "https://pytorch.org" },
  { name: "scikit-learn", url: "https://scikit-learn.org" },
  { name: "FastAPI", url: "https://fastapi.tiangolo.com" },
  { name: "React", url: "https://react.dev" },
  { name: "Gemini API", url: "https://ai.google.dev/gemini-api" },
  { name: "Auth0", url: "https://auth0.com" },
  { name: "Vultr", url: "https://www.vultr.com" },
  { name: "Caddy", url: "https://caddyserver.com" },
  { name: "PostgreSQL", url: "https://www.postgresql.org" },
];

export const TEAM: Member[] = [
  {
    name: "Abdul Sidani",
    github: "https://github.com/abdulksidani-png",
    linkedin: "https://www.linkedin.com/in/abdulrahman-sidani/",
    // TODO: replace with personal website
    website: "https://www.linkedin.com/in/abdulrahman-sidani/",
  },
  {
    name: "Benjamin Berrizbeitia",
    github: "https://github.com/Benberrizb",
    linkedin: "https://www.linkedin.com/in/berrizbeitia/",
    // TODO: replace with personal website
    website: "https://www.linkedin.com/in/berrizbeitia/",
  },
  {
    name: "Gayathri Gunda",
    github: "https://github.com/Gayathri-Gunda",
    linkedin: "https://www.linkedin.com/in/gayathri-gunda/",
    // TODO: replace with personal website
    website: "https://www.linkedin.com/in/gayathri-gunda/",
  },
  {
    name: "Vitor Ribeiro",
    github: "https://github.com/bolachala",
    linkedin: "https://www.linkedin.com/in/vitor-gonzaga-feres-ribeiro-41b572339/",
    // TODO: replace with personal website
    website: "https://www.linkedin.com/in/vitor-gonzaga-feres-ribeiro-41b572339/",
  },
];
