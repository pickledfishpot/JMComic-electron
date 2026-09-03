/** Clay 品牌色轮换主题：首页区块、筛选 pills、标签等按索引取色 */

export interface BrandTheme {
  /** 实心背景 class（特色卡 / 激活 pill） */
  bg: string;
  /** 实心背景上的文字 class */
  onBg: string;
  /** 区块标题文字色 */
  title: string;
  /** 浅色底（15-25% 透明度）class */
  soft: string;
}

export const BRAND_THEMES: BrandTheme[] = [
  { bg: "bg-brand-pink", onBg: "text-white", title: "text-brand-pink", soft: "bg-brand-pink/10" },
  { bg: "bg-brand-teal", onBg: "text-white", title: "text-brand-teal", soft: "bg-brand-teal/10" },
  { bg: "bg-brand-lavender", onBg: "text-ink", title: "text-brand-lavender", soft: "bg-brand-lavender/15" },
  { bg: "bg-brand-peach", onBg: "text-ink", title: "text-brand-peach", soft: "bg-brand-peach/20" },
  { bg: "bg-brand-ochre", onBg: "text-ink", title: "text-brand-ochre", soft: "bg-brand-ochre/15" },
  { bg: "bg-brand-coral", onBg: "text-white", title: "text-brand-coral", soft: "bg-brand-coral/10" },
];

export function brandTheme(index: number): BrandTheme {
  return BRAND_THEMES[index % BRAND_THEMES.length];
}

/** PillTabs 直接消费：激活态完整 class */
export const BRAND_PILL_COLORS = BRAND_THEMES.map((t) => `${t.bg} ${t.onBg}`);
