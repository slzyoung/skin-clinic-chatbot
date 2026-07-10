import { 
  RiRobot2Line, 
  RiSearchLine,
  RiCalendarLine,
  RiMessageAi3Line
} from "@remixicon/react";
import { Input } from "@/components/ui/input";

const searchResults = [
  {
    id: "1",
    title: "Bisakah Anda merekomendasikan produk untuk kondisi ini, jerawat di wajah",
    date: "4/27/2026 04:15 PM",
    messages: 12
  },
  {
    id: "2",
    title: "Buatkan rencana perawatan untuk pasien dengan dokumen yang telah saya sertakan",
    date: "4/27/2026 04:00 PM",
    messages: 13
  },
  {
    id: "3",
    title: "Apa penyebab umum jerawat hormonal dan langkah apa yang dapat diambil untuk mengurangi peradangan serta bekasnya?",
    date: "4/27/2026 03:45 PM",
    messages: 14
  },
  {
    id: "4",
    title: "Apa metode efektif untuk mengatasi kulit kering kronis yang sering kali disebabkan oleh eksim dan bagaimana cara memilih produk yang tepat?",
    date: "4/27/2026 03:15 PM",
    messages: 16
  },
  {
    id: "5",
    title: "Bagaimana perawatan yang sesuai untuk mengurangi kemerahan dan iritasi pada kulit sensitif dengan kondisi rosacea?",
    date: "4/27/2026 03:00 PM",
    messages: 17
  },
  {
    id: "6",
    title: "Langkah apa yang harus diambil untuk mencegah infeksi sekunder pada luka kulit yang disebabkan oleh gigitan serangga?",
    date: "4/27/2026 02:45 PM",
    messages: 18
  },
  {
    id: "7",
    title: "Bagaimana cara menentukan apakah bercak kulit gelap merupakan tanda hiperpigmentasi atau masalah lain yang memerlukan evaluasi medis?",
    date: "4/27/2026 02:30 PM",
    messages: 19
  }
];

export default function DoctorSearchPage() {
  return (
    <div className="flex flex-col max-w-2xl mx-auto min-h-full w-full px-4">
      {/* Sticky Top Section */}
      <div className="sticky top-0 z-10 bg-white pt-10 pb-8">
        {/* Header */}
        <div className="flex flex-col items-center text-center space-y-2 mb-8">
          <div className="flex aspect-square size-8 items-center justify-center rounded-md bg-blue-50 text-blue-500">
            <RiRobot2Line className="size-4" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-950">
            Hello Doctor, I&apos;m Ready to Help!
          </h1>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
            <RiSearchLine className="size-5 text-zinc-950" />
          </div>
          <Input
            type="text"
            className="w-full bg-white-500 rounded-xl py-3 pl-11 pr-4 text-sm text-zinc-950 placeholder:text-zinc-500 border-transparent focus-visible:border-blue-500"
            placeholder="Enter a keyword to search the chat"
          />
        </div>
      </div>

      {/* Search Results */}
      <div className="space-y-3 pb-12">
        {searchResults.map((chat) => (
          <div key={chat.id} className="bg-white rounded-xl p-3 border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 transition-colors cursor-pointer block">
            <p className="text-zinc-950 text-sm font-medium leading-snug truncate mb-2">
              {chat.title}
            </p>
            <div className="flex items-center gap-4 mt-auto">
              <div className="flex items-center text-zinc-500">
                <RiCalendarLine className="size-4 mr-1 text-zinc-950" />
                <span className="text-xs">{chat.date}</span>
              </div>
              <div className="flex items-center text-zinc-500 ml-auto">
                <RiMessageAi3Line className="size-4 mr-1 text-zinc-950" />
                <span className="text-xs">{chat.messages}</span>
              </div>
            </div>
          </div>
        ))}
        {/* Explicit physical spacer for bottom gap */}
        <div className="h-12 w-full shrink-0" />
      </div>
    </div>
  );
}
