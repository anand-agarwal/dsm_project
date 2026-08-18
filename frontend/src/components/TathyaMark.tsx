import { AGENT_NAME } from "@/agent/identity";
import { cn } from "@/lib/utils";

export type TathyaPose = "idle" | "wave" | "think" | "grow";

export function TathyaMark({
  pose = "idle",
  size = 40,
  animate = true,
  className,
  decorative = true,
}: {
  pose?: TathyaPose;
  size?: number;
  animate?: boolean;
  className?: string;
  decorative?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 80 100"
      width={size}
      height={size}
      role={decorative ? "presentation" : "img"}
      aria-hidden={decorative}
      aria-label={decorative ? undefined : AGENT_NAME}
      data-pose={pose}
      data-animate={animate ? "1" : "0"}
      className={cn("tathya-mark shrink-0 select-none", className)}
    >
      <g className="tathya-bot">
        <rect className="tathya-shadow" x="22" y="91" width="36" height="3.5" rx="1.75" fill="#DDDBDE" />

        <g className="tathya-barbell">
          <rect x="16" y="63.5" width="48" height="3" rx="1.5" fill="#B2ACB5" />
          <rect x="14" y="59" width="8" height="12" rx="2" fill="#241D2E" />
          <rect x="58" y="59" width="8" height="12" rx="2" fill="#241D2E" />
        </g>

        <g className="tathya-plant">
          <rect x="34" y="70" width="12" height="10" rx="2" fill="#6B3A22" />
          <ellipse cx="40" cy="66" rx="8" ry="7" fill="#5BA85A" />
          <ellipse cx="35" cy="67" rx="4" ry="3.5" fill="#6FBF6A" />
          <ellipse cx="45" cy="67.5" rx="3.5" ry="3" fill="#4E9450" />
        </g>

        <rect className="tathya-torso" x="32" y="60" width="16" height="14" rx="6" fill="#EF6329" />
        <g className="tathya-arms-down">
          <rect x="24" y="63" width="9" height="13" rx="4.5" fill="#EF6329" />
          <rect x="47" y="63" width="9" height="13" rx="4.5" fill="#EF6329" />
        </g>
        <g className="tathya-arms-up">
          <rect x="22" y="56" width="9" height="13" rx="4.5" fill="#EF6329" transform="rotate(-28 26.5 62.5)" />
          <rect x="49" y="56" width="9" height="13" rx="4.5" fill="#EF6329" transform="rotate(28 53.5 62.5)" />
        </g>
        <g className="tathya-hands-hold">
          <rect x="27" y="66" width="8" height="8" rx="4" fill="#EF6329" />
          <rect x="45" y="66" width="8" height="8" rx="4" fill="#EF6329" />
        </g>

        <rect className="tathya-ear" x="8" y="30" width="8" height="13" rx="2.5" fill="#241D2E" />
        <rect className="tathya-ear" x="64" y="30" width="8" height="13" rx="2.5" fill="#241D2E" />
        <path
          className="tathya-tuft"
          d="M52 8 L60 4 L61 16 Z"
          fill="#EF6329"
        />
        <rect x="14" y="12" width="52" height="48" rx="16" fill="#EF6329" />
        <rect x="21" y="21" width="38" height="30" rx="10" fill="#241D2E" />

        <g className="tathya-eyes-round">
          <circle cx="33" cy="35" r="4.2" fill="#F9F9F9" />
          <circle cx="47" cy="35" r="4.2" fill="#F9F9F9" />
        </g>
        <g className="tathya-eyes-happy">
          <path d="M28 36 Q33 31 38 36" fill="none" stroke="#F9F9F9" strokeWidth="2.6" strokeLinecap="round" />
          <path d="M42 36 Q47 31 52 36" fill="none" stroke="#F9F9F9" strokeWidth="2.6" strokeLinecap="round" />
        </g>
        <g className="tathya-eyes-focus">
          <path d="M28 33 Q33 38 38 33" fill="none" stroke="#F9F9F9" strokeWidth="2.6" strokeLinecap="round" />
          <path d="M42 33 Q47 38 52 33" fill="none" stroke="#F9F9F9" strokeWidth="2.6" strokeLinecap="round" />
        </g>
        <g className="tathya-eyes-star">
          <path
            transform="translate(33 35) scale(0.72)"
            fill="#F9F9F9"
            d="M0-7.2 L1.7-2.2 7-2.2 2.7 1 4.4 6.2 0 3.2-4.4 6.2-2.7 1-7-2.2-1.7-2.2Z"
          />
          <path
            transform="translate(47 35) scale(0.72)"
            fill="#F9F9F9"
            d="M0-7.2 L1.7-2.2 7-2.2 2.7 1 4.4 6.2 0 3.2-4.4 6.2-2.7 1-7-2.2-1.7-2.2Z"
          />
        </g>
        <path className="tathya-mouth" d="M37 44 Q40 47 43 44" fill="none" stroke="#F9F9F9" strokeWidth="1.8" strokeLinecap="round" />
      </g>
    </svg>
  );
}
