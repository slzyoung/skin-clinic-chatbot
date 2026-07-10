import { RiFilePdf2Line, RiCloseLine, RiRobot2Line, RiAttachmentLine, RiMedicineBottleLine, RiSyringeLine, RiMegaphoneLine, RiCornerDownLeftLine, RiUser3Line } from "@remixicon/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  MessageScrollerProvider,
  MessageScroller,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
} from "@/components/ui/message-scroller"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function ChatPreview() {
  return (
    <div className="flex flex-col flex-1 bg-white overflow-hidden min-h-0 h-full">
      <MessageScrollerProvider>
        <MessageScroller className="flex-1 min-h-0">
          <MessageScrollerViewport className="px-8">
            <MessageScrollerContent className="py-10 gap-6 w-full max-w-4xl mx-auto">
              {/* Uploaded Files Bubbles */}
              <MessageScrollerItem>
                <div className="flex justify-end gap-4 w-full">
                  <div className="flex items-center gap-2 px-2 py-2 rounded-md border border-black/10 bg-white">
                    <div className="bg-red-100 p-1.5 rounded text-red-900">
                      <RiFilePdf2Line className="size-4" />
                    </div>
                    <div className="flex flex-col justify-center">
                      <span className="text-xs font-medium text-zinc-950 truncate max-w-35">Profil_Hamdan_Zakirun_Naik</span>
                      <span className="text-[10px] text-zinc-500">PDF</span>
                    </div>
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-zinc-400 hover:text-zinc-600 ml-1 rounded-full hover:bg-zinc-100">
                      <RiCloseLine className="size-4" />
                    </Button>
                  </div>
                  
                  <div className="flex items-center gap-2 px-2 py-2 rounded-md border border-black/10 bg-white">
                    <div className="bg-red-100 p-1.5 rounded text-red-900">
                      <RiFilePdf2Line className="size-4" />
                    </div>
                    <div className="flex flex-col justify-center">
                      <span className="text-xs font-medium text-zinc-950 truncate max-w-35">ERHA Acne Spot Gel Protocol</span>
                      <span className="text-[10px] text-zinc-500">PDF</span>
                    </div>
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-zinc-400 hover:text-zinc-600 ml-1 rounded-full hover:bg-zinc-100">
                      <RiCloseLine className="size-4" />
                    </Button>
                  </div>
                </div>
              </MessageScrollerItem>

              {/* AI Assistant Blue Bubble */}
              <MessageScrollerItem>
                <div className="flex items-start gap-3 w-full">
                  <div className="bg-zinc-100 rounded text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiRobot2Line className="size-4" />
                  </div>
                  <div className="bg-blue-50 text-zinc-950 p-3 rounded-md text-sm w-full">
                    This document provides an overview of a skin concern and emphasizes the necessity of a certain product for its resolution.
                  </div>
                </div>
              </MessageScrollerItem>

              {/* AI Extracting Markdown Message */}
              <MessageScrollerItem>
                <div className="flex items-start gap-3 w-full">
                  <div className="bg-zinc-100 rounded text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiRobot2Line className="size-4" />
                  </div>
                  <div className="text-sm text-zinc-950 leading-relaxed w-full pt-1.5">
                    Analysis complete. I&apos;ve extracted the text from ERHA Acne Spot Gel Protocol.pdf into markdown format for your review
                  </div>
                </div>
              </MessageScrollerItem>

              {/* Extracted Document Card */}
              <MessageScrollerItem>
                <div className="flex items-start gap-3 w-full">
                  <div className="w-7 shrink-0" />
                  <div className="border border-black/10 rounded-md p-4 bg-white w-full">
                    <div className="flex items-center gap-2 mb-4">
                      <RiFilePdf2Line className="size-5 text-zinc-950" />
                      <h3 className="font-medium text-zinc-950">ERHA Acne Spot Gel Protocol</h3>
                    </div>

                    <div className="text-sm text-zinc-800 space-y-4 leading-relaxed">
                      <p>
                        <strong>ERHA Acne Spot Gel Protocol (v1.0)</strong><br/>
                        This protocol describes the standardized clinical formulation review, quality assessment, and knowledge extraction procedure for ERHA Acne Spot Gel. The product is intended for localized application on acne lesions and should be classified as a targeted acne management product, not a full-face treatment protocol.
                      </p>
                      
                      <p>
                        <strong>Formulation and Active Component Review</strong><br/>
                        <strong>Salicylic Acid:</strong> Supports keratolytic activity by promoting exfoliation within the follicular opening and reducing pore obstruction.<br/>
                        <strong>Sulfur-Based Component:</strong> Assists in drying active lesions and reducing excess surface oil in acne-prone areas.<br/>
                        <strong>Niacinamide:</strong> Supports reduction of visible redness and improves the appearance of post-inflammatory skin changes.<br/>
                        <strong>Zinc PCA:</strong> Contributes to sebum regulation and supports control of acne-associated microbial imbalance.
                      </p>

                      <h4 className="text-blue-600 font-semibold pt-2">Clinical Quality Parameters</h4>
                      
                      <div className="border border-black/10 rounded-md overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-[33%] font-normal text-zinc-950">Parameter</TableHead>
                              <TableHead className="w-[33%] font-normal text-zinc-950">Target Range</TableHead>
                              <TableHead className="w-[33%] font-normal text-zinc-950">Critical Limit</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            <TableRow>
                              <TableCell>Viscosity</TableCell>
                              <TableCell>900 - 1300 cP</TableCell>
                              <TableCell>{">"} 1600 cP</TableCell>
                            </TableRow>
                            <TableRow>
                              <TableCell>pH Balance</TableCell>
                              <TableCell>4.5 - 5.5</TableCell>
                              <TableCell>{"<"} 4.0 or {">"} 6.0</TableCell>
                            </TableRow>
                            <TableRow>
                              <TableCell>Spreadability</TableCell>
                              <TableCell>3.0 - 4.5 cm</TableCell>
                              <TableCell>{"<"} 2.5 cm</TableCell>
                            </TableRow>
                            <TableRow>
                              <TableCell>Drying Time</TableCell>
                              <TableCell>1 - 3 minutes</TableCell>
                              <TableCell>{">"} 5 minutes</TableCell>
                            </TableRow>
                            <TableRow>
                              <TableCell>Microbial Limit</TableCell>
                              <TableCell>Within topical product standard</TableCell>
                              <TableCell>Exceeds accepted limit</TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>

                      <p>
                        <strong>Clinical Use Classification</strong><br/>
                        The product should be tagged as a topical acne spot treatment. Recommended metadata classification includes dermatology, acne care, localized lesion treatment, oily and acne-prone skin, and doctor-directed product recommendation. The product should not be classified as a systemic acne therapy or prescription-only treatment unless supported by verified regulatory documentation.
                      </p>

                      <p>
                        <strong>Safety and Application Notes</strong><br/>
                        Apply a thin layer only to affected acne areas after cleansing. Avoid use around the eyes, lips, mucosal areas, and open wounds. Monitor for excessive dryness, irritation, peeling, or burning sensation. Daytime use should be accompanied by sunscreen when clinically appropriate. Use frequency and duration should follow product label instructions or doctor recommendation.
                      </p>

                      <p>
                        <strong>Knowledge Extraction Notes</strong><br/>
                        The AI identified inconsistent wording between product benefit claims and clinical treatment claims. The marketing brochure describes visible acne reduction, while the clinical reference document emphasizes targeted lesion management. Manual validation is required to ensure the chatbot does not overstate efficacy, imply guaranteed outcomes, or recommend full-face application without supporting evidence.
                      </p>

                      <p>
                        <strong>Medical Review Status</strong><br/>
                        This document should remain under medical review until the active ingredient list, concentration data, safety warnings, product version, and approved claims are verified against the latest official product label or internal clinical documentation. Only validated content should be published to the chatbot knowledge base.
                      </p>
                    </div>
                  </div>
                </div>
              </MessageScrollerItem>

              {/* User Text Bubble */}
              <MessageScrollerItem scrollAnchor>
                <div className="flex items-start gap-3 mt-2 flex-row-reverse w-full">
                  <div className="bg-zinc-100 rounded text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiUser3Line className="size-4" />
                  </div>
                  <div className="bg-blue-500 text-white p-3 rounded-md text-sm w-full">
                    Please analyze these documents and extract the key information for the Acne Spot Gel Protocol.
                  </div>
                </div>
              </MessageScrollerItem>
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>
      
      {/* Chatbox Input */}
      <div className="px-8 py-4 shrink-0">
        <div className="bg-white-500 rounded-md p-4 flex flex-col gap-4 border border-black/10">
          <Input 
            placeholder="Reply here..." 
            className="w-full bg-transparent border-none shadow-none focus-visible:ring-0 px-0 outline-none text-sm text-gray-700 placeholder:text-gray-500"
          />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button variant="outline" className="gap-1.5 bg-white text-gray-700 hover:bg-gray-50 border-gray-200">
                <RiAttachmentLine className="w-4 h-4" />
                attach file
              </Button>
              <Button variant="outline" className="gap-1.5 bg-white text-gray-700 hover:bg-gray-50 border-gray-200">
                <RiMedicineBottleLine className="w-4 h-4" />
                Product
              </Button>
              <Button variant="outline" className="gap-1.5 bg-white text-gray-700 hover:bg-gray-50 border-gray-200">
                <RiSyringeLine className="w-4 h-4" />
                Treatment
              </Button>
              <Button variant="outline" className="gap-1.5 bg-white text-gray-700 hover:bg-gray-50 border-gray-200">
                <RiMegaphoneLine className="w-4 h-4" />
                Promotional
              </Button>
            </div>
            <Button size="icon" className="bg-blue-500 text-white hover:bg-blue-600 shrink-0">
              <RiCornerDownLeftLine className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
