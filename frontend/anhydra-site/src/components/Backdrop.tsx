import { useState } from "react";

export const PHOTO = "https://irp.cdn-website.com/9ec79508/dms3rep/multi/opt/tardigrade-sem-base";
// Upscaled copies made on the server by scripts/upscale_backdrop.py. If they are missing, the photo
// falls back to Duda's image server.
const LOCAL = "/backdrop/tardigrade";

export function Backdrop({ still = false }: { still?: boolean }) {
  const [local, setLocal] = useState(true);
  return (
    <div className={still ? "backdrop still" : "backdrop"} aria-hidden="true">
      {local ? (
        <img
          key="local"
          src={`${LOCAL}-1920w.webp`}
          srcSet={`${LOCAL}-1280w.webp 1280w, ${LOCAL}-1920w.webp 1920w, ${LOCAL}-2560w.webp 2560w, ${LOCAL}-3840w.webp 3840w`}
          sizes="100vw"
          width={1000}
          height={721}
          alt=""
          fetchPriority={still ? undefined : "high"}
          onError={() => setLocal(false)}
        />
      ) : (
        <img
          key="duda"
          src={`${PHOTO}-1200w.png`}
          srcSet={`${PHOTO}-800w.png 800w, ${PHOTO}-1200w.png 1200w, ${PHOTO}-1920w.png 1920w`}
          sizes="100vw"
          width={1000}
          height={721}
          alt=""
          fetchPriority={still ? undefined : "high"}
        />
      )}
      <div className="backdrop-shade" />
    </div>
  );
}
