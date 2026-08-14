import type { Category } from '@/types/inventoryTypes';

const CATEGORY_OPTIONS: { title: string; value: Category }[] = [
  { title: 'Allgemein', value: 'general' },
  { title: 'Werkzeuge', value: 'tools' },
  { title: 'Pflanzen', value: 'plants' },
  { title: 'Flüssigkeiten', value: 'fluids' },
  { title: 'Baumaterialien', value: 'hardware' },
  { title: 'Elektrik', value: 'electrical' },
  { title: 'Befestigungsmaterial', value: 'fasteners' },
  { title: 'Holz', value: 'wood' },
  { title: 'Metall', value: 'metal' },
  { title: 'Farbe', value: 'paint' },
  { title: 'Klebstoffe', value: 'adhesives' },
  { title: 'Sanitär', value: 'plumbing' },
  { title: 'Bewässerung', value: 'irrigation' },
  { title: 'Dünger', value: 'fertilizer' },
  { title: 'Boden', value: 'soil' },
  { title: 'Samen', value: 'seeds' },
  { title: 'Töpfe', value: 'pots' },
  { title: 'Reinigung', value: 'cleaning' },
  { title: 'Sicherheit', value: 'safety' },
  { title: 'Lagerung', value: 'storage' },
  { title: 'Maschinen', value: 'machines' },
  { title: 'Ersatzteile', value: 'spare-parts' },
  { title: 'Verbrauchsmaterialien', value: 'consumables' },
  { title: 'Sonstiges', value: 'other' },
];

export { CATEGORY_OPTIONS };
