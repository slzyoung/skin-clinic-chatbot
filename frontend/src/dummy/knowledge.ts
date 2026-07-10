export const knowledgeTableData = [
  {
    id: 1,
    title: "ERHA Acne Spot Gel",
    subtitle: "150 ml",
    image: "/mini-placeholder.svg",
    category: "Acne Care",
    description:
      "Memperkenalkan ERHA Acne Spot Gel, solusi ampuh yang dirancang untuk menargetkan dan mengurangi noda jerawat yang membandel. Diformulasikan dengan bahan-bahan kuat...",
    status: "Approved",
  },
  {
    id: 2,
    title: "ERHA Acne Cleanser",
    subtitle: "150 ml",
    image: "/mini-placeholder.svg",
    category: "Acne Care",
    description: "JoleneFaolan@gmail.com", // Keeping verbatim from figma
    status: "Approved",
  },
  {
    id: 3,
    title: "ERHA Brightening Serum",
    subtitle: "150 ml",
    image: "/mini-placeholder.svg",
    category: "Brightening",
    description:
      "Serum Pencerah ERHA adalah solusi sempurna untuk kulit bercahaya dan merata. Diperkaya dengan bahan aktif yang efektif...",
    status: "Approved",
  },
];

export type KnowledgeItem = typeof knowledgeTableData[0]
