"use client";

import { Button } from "@/components/ui/button";
import { RiArrowLeftLine, RiCheckLine, RiDeleteBin7Line, RiEdit2Line } from "@remixicon/react";
import { useRouter } from "next/navigation";
import { use, useState, useRef } from "react";
import { useKnowledgeBatch, useDeleteKnowledge } from "../../hooks/use-knowledge";
import { BatchKnowledgeTabContent, BatchTabHandle } from "./BatchKnowledgeTabContent";
import { useSession } from "@/hooks/use-session";
import { toast } from "sonner";

export default function BatchKnowledgePage({ params }: { params: Promise<{ id: string }> }) {
	const router = useRouter();
	const unwrappedParams = use(params);
	const batchId = unwrappedParams.id;
	const { data: batchDocuments, isLoading, error } = useKnowledgeBatch(batchId);
	const [activeTab, setActiveTab] = useState<string | undefined>(undefined);
	const { user } = useSession();
	const hasWriteAccess = user?.accesses?.includes("knowledge:write");
	const hasDeleteAccess = user?.accesses?.includes("knowledge:delete");
	const deleteMutation = useDeleteKnowledge();

	const [editModes, setEditModes] = useState<Record<string, boolean>>({});
	const tabRefs = useRef<Record<string, BatchTabHandle | null>>({});

	if (error) {
		return (
			<div className="flex items-center justify-center h-full text-red-500">
				Error loading batch details
			</div>
		);
	}

	if (isLoading || !batchDocuments) {
		return (
			<div className="flex items-center justify-center h-full text-zinc-500">
				Loading batch documents...
			</div>
		);
	}

	if (batchDocuments.length === 0) {
		return (
			<div className="flex items-center justify-center h-full text-zinc-500">
				No documents found for this batch.
			</div>
		);
	}

	const currentTab = activeTab || batchDocuments[0].id;
	const activeDoc = batchDocuments.find(d => d.id === currentTab) || batchDocuments[0];
	
	const batchFeedbacks = batchDocuments
		.map((d, i) => {
			const feedback = (d.metadata as Record<string, unknown>)?.feedback as string | undefined;
			if (!feedback) return null;
			const title = d.title || `Document ${i + 1}`;
			return `• ${title}:\n  ${feedback}`;
		})
		.filter(Boolean);
	
	const batchFeedback = batchFeedbacks.length > 0 
		? batchFeedbacks.join("\n\n") 
		: undefined;

	const isEditMode = editModes[currentTab] || false;

	const handleEditToggle = async () => {
		if (isEditMode) {
			await tabRefs.current[currentTab]?.handleSave();
		} else {
			toast.info("You can now edit the document categories below.");
			setEditModes(prev => ({ ...prev, [currentTab]: true }));
		}
	};

	const handleDelete = async () => {
		await tabRefs.current[currentTab]?.handleDelete();
	};

	return (
		<div className="flex flex-col absolute inset-0 bg-zinc-50/50">
			{/* Batch Header */}
			<div className="flex items-center gap-4 p-4 border-b border-gray-200 shrink-0 bg-white justify-between">
				<div className="flex items-center gap-4">
					<Button
						variant="ghost"
						size="icon"
						onClick={() => router.back()}
						className="text-gray-500 hover:text-gray-900"
					>
						<RiArrowLeftLine className="size-5" />
					</Button>
					<div>
						<h1 className="text-lg font-semibold text-gray-900">Batch Review Session</h1>
						<p className="text-sm text-gray-500">{batchDocuments.length} documents uploaded</p>
					</div>
				</div>

				<div className="flex items-center gap-2">
					{hasDeleteAccess && activeDoc?.status === "APPROVED" && (
						<Button
							onClick={handleDelete}
							disabled={deleteMutation.isPending || isLoading}
							variant="outline"
							className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
						>
							<RiDeleteBin7Line className="size-4" />
							Delete Knowledge
						</Button>
					)}
					{hasWriteAccess && activeDoc?.status === "APPROVED" && (
						<Button
							variant={isEditMode ? "default" : "outline"}
							className={`gap-2 ${isEditMode ? "bg-emerald-600 hover:bg-emerald-700 text-white" : "text-zinc-950"}`}
							disabled={isLoading}
							onClick={handleEditToggle}
						>
							{isEditMode ? <RiCheckLine className="size-4" /> : <RiEdit2Line className="size-4" />}
							{isEditMode ? "Save" : "Edit Knowledge"}
						</Button>
					)}
				</div>
			</div>

			{batchFeedback && (
				<div className="bg-blue-50/50 border-b border-blue-100 px-6 py-4 shrink-0 flex items-start gap-3">
					<div className="p-2 bg-blue-100 text-blue-700 rounded-lg shrink-0 mt-0.5">
						<RiArrowLeftLine className="size-4 opacity-0 absolute" /> {/* Spacer trick to align icon nicely */}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-4">
							<path d="M11 14.0619V20H13V14.0619C16.9463 13.5539 20 10.1274 20 6H4C4 10.1274 7.05369 13.5539 11 14.0619ZM12 22C7.58172 22 4 18.4183 4 14C4 12.336 4.50974 10.7915 5.37803 9.5H18.622C19.4903 10.7915 20 12.336 20 14C20 18.4183 16.4183 22 12 22ZM2 4H22V2H2V4Z"></path>
						</svg>
					</div>
					<div>
						<h3 className="text-sm font-semibold text-blue-900 mb-1">Executive Summary</h3>
						<p className="text-sm text-blue-800 leading-relaxed whitespace-pre-wrap">{batchFeedback}</p>
					</div>
				</div>
			)}

			{/* Tabs Layout */}
			<div className="flex flex-col flex-1 overflow-hidden w-full">
				<div className="flex border-b border-zinc-200 bg-white overflow-x-auto scrollbar-hide shrink-0">
					{batchDocuments.map((doc, index) => (
						<button
							key={doc.id}
							onClick={() => setActiveTab(doc.id)}
							className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors flex items-center ${
								currentTab === doc.id
									? "border-b-2 border-blue-600 text-blue-700 bg-blue-50/50"
									: "text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50"
							}`}
						>
							<span className="truncate max-w-50">{doc.title || `Document ${index + 1}`}</span>
							{doc.status === "PROCESSING" && (
								<span className="ml-2 inline-flex items-center rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 shrink-0">
									Processing
								</span>
							)}
							{doc.status === "PENDING" && (
								<span className="ml-2 inline-flex items-center rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20 shrink-0">
									Review
								</span>
							)}
						</button>
					))}
				</div>

				<div className="flex-1 overflow-hidden relative">
					{batchDocuments.map((doc) => (
						<div
							key={doc.id}
							className={`absolute inset-0 m-0 flex flex-col ${currentTab !== doc.id ? "hidden" : ""}`}
						>
							<BatchKnowledgeTabContent 
								knowledgeId={doc.id}
								ref={(el) => { tabRefs.current[doc.id] = el; }}
								isEditMode={editModes[doc.id] || false}
								setIsEditMode={(v) => setEditModes(prev => ({ ...prev, [doc.id]: v }))}
							/>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}
