"use client";

import { ChatPreview } from "@/components/shared/knowledge/ChatPreview";
import { ClassificationSidebar } from "@/components/shared/knowledge/ClassificationSidebar";
import { Button } from "@/components/ui/button";
import { RiArrowLeftLine, RiDeleteBin7Line, RiEdit2Line } from "@remixicon/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use } from "react";
import { useDeleteKnowledge, useKnowledgeDetail } from "../hooks/use-knowledge";
import { useSession } from "@/hooks/use-session";

export default function KnowledgeDetailPage({ params }: { params: Promise<{ id: string }> }) {
	const router = useRouter();
	const unwrappedParams = use(params);
	const id = unwrappedParams.id;
	const { data, isLoading, error } = useKnowledgeDetail(id);
	const deleteMutation = useDeleteKnowledge();
	const { user } = useSession();
	const hasWriteAccess = user?.accesses?.includes("knowledge:write");
	const hasDeleteAccess = user?.accesses?.includes("knowledge:delete");

	const handleDelete = () => {
		if (confirm("Are you sure you want to delete this knowledge document?")) {
			deleteMutation.mutate(id, {
				onSuccess: () => {
					router.push("/dashboard/knowledge");
				},
			});
		}
	};

	if (error) {
		return (
			<div className="flex items-center justify-center h-full text-red-500">
				Error loading document details
			</div>
		);
	}

	return (
		<div className="flex flex-col absolute inset-0">
			{/* Title Header with Actions */}
			<div className="px-6 py-3 border-b border-black/10 bg-white shrink-0 flex items-center justify-between">
				<Link
					href="/dashboard/knowledge"
					className="flex items-center gap-2 text-zinc-950 hover:text-zinc-700 transition-colors"
				>
					<RiArrowLeftLine className="size-4" />
					<span className="text-sm font-semibold">{data?.title || "Knowledge Document"}</span>
				</Link>

				<div className="flex items-center gap-2">
					{hasDeleteAccess && (
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
					{hasWriteAccess && (
						<Button variant="outline" className="gap-2 text-zinc-950" disabled={isLoading}>
							<RiEdit2Line className="size-4" />
							Edit Knowledge
						</Button>
					)}
				</div>
			</div>

			{/* Main Content Area */}
			<div className="flex flex-1 overflow-hidden">
				{/* Left Column (Chat / Preview) */}
				<ChatPreview
					knowledgeId={data?.id}
					knowledgeStatus={data?.status}
					aiSummary={data?.ai_summary}
					fileName={data?.file_name || data?.title}
					isDetailLoading={isLoading}
				/>

				{/* Right Column (Classification) */}
				<ClassificationSidebar knowledge={data} />
			</div>
		</div>
	);
}
