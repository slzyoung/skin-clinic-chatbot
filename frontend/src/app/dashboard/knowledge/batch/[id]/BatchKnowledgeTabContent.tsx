"use client";

import { ChatPreview } from "@/app/dashboard/knowledge/components/preview/chat-preview";
import { ConfirmationModal } from "@/components/shared/confirmation-modal";
import { useState, forwardRef, useImperativeHandle } from "react";
import {
	useKnowledgeDetail,
	useEditKnowledge,
	useDeleteKnowledge,
} from "../../hooks/use-knowledge";
import { KnowledgeResponse, VisibilitySettings } from "../../api/types";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export interface BatchTabHandle {
	handleSave: (newTitle?: string) => Promise<void>;
	handleDelete: () => Promise<void>;
}

interface BatchKnowledgeTabContentProps {
	knowledgeId: string;
	initialKnowledge?: KnowledgeResponse;
	isEditMode: boolean;
	setIsEditMode: (v: boolean) => void;
	headerNode?: React.ReactNode;
	preHeaderNode?: React.ReactNode;
	onDeleteSuccess?: (deletedId: string) => void;
}

export const BatchKnowledgeTabContent = forwardRef<BatchTabHandle, BatchKnowledgeTabContentProps>(
	(
		{
			knowledgeId,
			initialKnowledge,
			isEditMode,
			setIsEditMode,
			headerNode,
			preHeaderNode,
			onDeleteSuccess,
		},
		ref,
	) => {
		const { data, isLoading, error } = useKnowledgeDetail(knowledgeId);
		const editKnowledge = useEditKnowledge();
		const deleteMutation = useDeleteKnowledge();
		const router = useRouter();

		const doc = data || initialKnowledge;

		const initialCategories =
			(doc?.metadata?.categories as string[]) ||
			(doc?.metadata?.suggested_categories as Array<{ name: string }>)?.map((c) => c.name) ||
			[];
		const initialVisibility = (doc?.metadata?.visibility_settings as VisibilitySettings) || {
			clinics: ["all"],
			doctor_types: ["all"],
			doctors: ["all"],
		};

		const [pendingCategories, setPendingCategories] = useState<string[]>(initialCategories);
		const [pendingVisibilitySettings, setPendingVisibilitySettings] =
			useState<VisibilitySettings>(initialVisibility);
		const [pendingTitle, setPendingTitle] = useState(doc?.title || "");
		const [prevMetadataStr, setPrevMetadataStr] = useState(JSON.stringify(doc?.metadata || {}));
		const [prevTitle, setPrevTitle] = useState(doc?.title);
		const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

		if (JSON.stringify(doc?.metadata || {}) !== prevMetadataStr) {
			setPrevMetadataStr(JSON.stringify(doc?.metadata || {}));
			setPendingCategories(initialCategories);
			setPendingVisibilitySettings(initialVisibility);
		}

		if (doc?.title !== prevTitle && !isEditMode) {
			setPrevTitle(doc?.title);
			setPendingTitle(doc?.title || "");
		}

		const handleSave = async (newTitle?: string) => {
			await editKnowledge.mutateAsync({
				id: knowledgeId,
				data: {
					summary: doc?.ai_summary || "",
					categories: pendingCategories,
					visibility_settings: pendingVisibilitySettings,
					title: typeof newTitle === "string" ? newTitle : pendingTitle,
				},
			});
			setIsEditMode(false);
		};

		const handleDelete = async () => {
			await deleteMutation.mutateAsync(knowledgeId);
			toast.success("Knowledge deleted successfully");
			if (onDeleteSuccess) {
				onDeleteSuccess(knowledgeId);
			} else {
				router.push("/dashboard/knowledge");
			}
		};

		useImperativeHandle(ref, () => ({
			handleSave,
			handleDelete: async () => {
				setIsDeleteModalOpen(true);
			},
		}));

		if (error && !doc) {
			return (
				<div className="flex items-center justify-center h-full text-red-500">
					Error loading document details
				</div>
			);
		}

		const handleCancel = () => {
			setPendingCategories(initialCategories);
			setPendingVisibilitySettings(initialVisibility);
			setPendingTitle(doc?.title || "");
			setIsEditMode(false);
		};

		return (
			<div className="flex flex-col h-full bg-white relative">
				{/* Main Content Area */}
				<div className="flex flex-1 overflow-hidden">
					{/* Left Column (Chat / Preview) */}
					<ChatPreview
						mode="knowledge"
						knowledgeId={knowledgeId}
						knowledge={doc}
						knowledgeStatus={doc?.status}
						aiSummary={doc?.ai_summary}
						fileName={doc?.file_name}
						initialPrompt={(doc?.metadata?.initial_prompt as string) || undefined}
						files={(doc?.metadata?.files as { file_name: string; summary: string }[]) || []}
						isDetailLoading={isLoading && !doc}
						isEditMode={isEditMode}
						categories={pendingCategories}
						onChangeCategories={setPendingCategories}
						visibilitySettings={pendingVisibilitySettings}
						onChangeVisibilitySettings={setPendingVisibilitySettings}
						title={pendingTitle}
						onChangeTitle={setPendingTitle}
						onSave={handleSave}
						onCancel={handleCancel}
						headerNode={headerNode}
						preHeaderNode={preHeaderNode}
					/>
				</div>

				{/* Delete Confirmation Modal */}
				<ConfirmationModal
					isOpen={isDeleteModalOpen}
					onOpenChange={setIsDeleteModalOpen}
					title="Delete Knowledge?"
					description="Are you certain you want to delete this knowledge? If you proceed, it will be removed from the chatbot."
					confirmText="Delete Knowledge"
					cancelText="Cancel"
					isLoading={deleteMutation.isPending}
					onConfirm={handleDelete}
				/>
			</div>
		);
	},
);
BatchKnowledgeTabContent.displayName = "BatchKnowledgeTabContent";
