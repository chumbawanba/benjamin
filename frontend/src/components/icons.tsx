interface IconProps {
  className?: string;
}

// Ícones minimalistas em traço (stroke), consistentes com o estilo do ThemeToggle.tsx
// já existente - usados na NavBar (mobile, em baixo) e na SideNav (desktop, à esquerda).
const defaultProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

export function IconHome({ className = 'w-5 h-5' }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" {...defaultProps} className={className}>
      <path d="M4 11.5 12 4l8 7.5" />
      <path d="M6 10v8.5a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1V10" />
    </svg>
  );
}

export function IconWallet({ className = 'w-5 h-5' }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" {...defaultProps} className={className}>
      <path d="M4 7a2 2 0 0 1 2-2h11a1 1 0 0 1 1 1v2" />
      <rect x="3" y="8" width="18" height="11" rx="2" />
      <circle cx="16.5" cy="13.5" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconSliders({ className = 'w-5 h-5' }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" {...defaultProps} className={className}>
      <line x1="4" y1="6" x2="20" y2="6" />
      <circle cx="9" cy="6" r="2" fill="currentColor" stroke="none" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="11" cy="18" r="2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconLogout({ className = 'w-5 h-5' }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" {...defaultProps} className={className}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
