import { KnowledgeSummary } from "@/components/shared/knowledge/knowledge-summary";
import { KnowledgeTable } from "@/components/shared/knowledge/knowledge-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function KnowledgePage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <KnowledgeSummary />

        <div className="mt-8">
          <Tabs defaultValue="product" className="w-full">
            <div className="flex justify-between items-end mb-0">
              <TabsList variant="line" className="m-0">
                <TabsTrigger 
                  value="product"
                  className="font-medium text-sm text-gray-500 hover:text-blue-500 data-active:text-blue-500 data-active:after:bg-blue-500"
                >
                  Product
                </TabsTrigger>
                <TabsTrigger 
                  value="treatment"
                  className="font-medium text-sm text-gray-500 hover:text-blue-500 data-active:text-blue-500 data-active:after:bg-blue-500"
                >
                  Treatment
                </TabsTrigger>
                <TabsTrigger 
                  value="promotional"
                  className="font-medium text-sm text-gray-500 hover:text-blue-500 data-active:text-blue-500 data-active:after:bg-blue-500"
                >
                  Promotional
                </TabsTrigger>
              </TabsList>
            </div>
            
            <TabsContent value="product" className="mt-0 outline-none">
              <KnowledgeTable />
            </TabsContent>
            
            <TabsContent value="treatment" className="mt-0 outline-none">
              <div className="text-gray-500 p-8 text-center border border-gray-200 border-dashed rounded-md bg-white">
                Treatment knowledge base content will appear here.
              </div>
            </TabsContent>
            
            <TabsContent value="promotional" className="mt-0 outline-none">
              <div className="text-gray-500 p-8 text-center border border-gray-200 border-dashed rounded-md bg-white">
                Promotional content will appear here.
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
