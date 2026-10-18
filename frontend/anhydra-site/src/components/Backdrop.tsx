export const PHOTO = "https://irp.cdn-website.com/9ec79508/dms3rep/multi/opt/tardigrade-sem-base";

export function Backdrop({ still = false }: { still?: boolean }) {
  return (
    <div className={still ? "backdrop still" : "backdrop"} aria-hidden="true">
      <img
        src={`${PHOTO}-1200w.png`}
        srcSet={`${PHOTO}-800w.png 800w, ${PHOTO}-1200w.png 1200w, ${PHOTO}-1920w.png 1920w`}
        sizes="100vw"
        width={1000}
        height={721}
        alt=""
        fetchPriority={still ? undefined : "high"}
      />
      <div className="backdrop-shade" />
    </div>
  );
}
