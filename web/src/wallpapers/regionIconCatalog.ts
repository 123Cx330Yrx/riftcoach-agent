export type RegionIconId =
  | "ixtal"
  | "mount-targon"
  | "freljord"
  | "demacia"
  | "shurima"
  | "shadow-isles"
  | "bilgewater"
  | "bandle-city"
  | "piltover"
  | "zaun"
  | "ionia"
  | "void"
  | "noxus"

export interface RegionIconAsset {
  readonly id: RegionIconId
  readonly label: Readonly<{ "zh-CN": string; en: string }>
  readonly asset: string
  readonly source: "riot-universe-region-crest"
}

const REGION_ICON_CATALOG = [
  ["ixtal", "以绪塔尔", "Ixtal", "ixtal_crest_icon"],
  ["mount-targon", "巨神峰", "Mount Targon", "mt_targon_crest_icon"],
  ["freljord", "弗雷尔卓德", "Freljord", "freljord_crest_icon"],
  ["demacia", "德玛西亚", "Demacia", "demacia_crest_icon"],
  ["shurima", "恕瑞玛", "Shurima", "shurima_crest_icon"],
  ["shadow-isles", "暗影岛", "Shadow Isles", "shadow_isles_crest_icon"],
  ["bilgewater", "比尔吉沃特", "Bilgewater", "bilgewater_crest_icon"],
  ["bandle-city", "班德尔城", "Bandle City", "bandle_city_crest_icon"],
  ["piltover", "皮尔特沃夫", "Piltover", "piltover_crest_icon"],
  ["zaun", "祖安", "Zaun", "zaun_crest_icon"],
  ["ionia", "艾欧尼亚", "Ionia", "iona_crest_icon"],
  ["void", "虚空之地", "The Void", "void_crest_icon"],
  ["noxus", "诺克萨斯", "Noxus", "noxus_crest_icon"],
] as const

export const regionIconCatalog: readonly RegionIconAsset[] = REGION_ICON_CATALOG.map(([id, zh, en, file]) => ({
  id,
  label: { "zh-CN": zh, en },
  asset: `/assets/wallpapers/regions/universe/${file}.png`,
  source: "riot-universe-region-crest" as const,
}))
