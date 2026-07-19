export type Branch = {
  id: string;
  name: string;
  address: string;
  tokensMonth: number;
  used: number;
  remaining: number;
  image?: string;
  logoUrl?: string;
};

export const mockBranches: Branch[] = [
  {
    id: "branch-1",
    name: "Erha Gunung Kidul",
    address: "Jl. Taman Bakti No.6, Purbosari, Wonosari, Kec. Wonosari, Kabupaten Gunungkidul, Daerah Istimewa Yogyakarta 55813",
    tokensMonth: 1000,
    used: 80,
    remaining: 920,
  },
  {
    id: "branch-2",
    name: "Erha Yogyakarta",
    address: "Pakuwon Mall Jogja, Lantai 1, Kaliwaru, Condongcatur, Kec. Depok, Kabupaten Sleman, Daerah Istimewa Yogyakarta 55281",
    tokensMonth: 1000,
    used: 80,
    remaining: 920,
  },
  {
    id: "branch-3",
    name: "Erha Sleman",
    address: "Jl. Supadi No.18, Kotabaru, Kec. Gondokusuman, Kota Yogyakarta, Daerah Istimewa Yogyakarta 55224",
    tokensMonth: 1000,
    used: 80,
    remaining: 920,
  }
];
