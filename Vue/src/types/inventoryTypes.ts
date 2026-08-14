interface inventoryItem {
  id: number;
  title: string;
  count: number;
  condition: 'new' | 'used' | 'damaged';
  category: Category;
  created_at: string; // ISO date string
  image?: string; // Optional property for the image URL or path
}

type Category =
  | 'general'
  | 'tools'
  | 'plants'
  | 'fluids'
  | 'hardware'
  | 'electrical'
  | 'fasteners'
  | 'wood'
  | 'metal'
  | 'paint'
  | 'adhesives'
  | 'plumbing'
  | 'irrigation'
  | 'fertilizer'
  | 'soil'
  | 'seeds'
  | 'pots'
  | 'cleaning'
  | 'safety'
  | 'storage'
  | 'machines'
  | 'spare-parts'
  | 'consumables'
  | 'other';

export type { inventoryItem, Category };
