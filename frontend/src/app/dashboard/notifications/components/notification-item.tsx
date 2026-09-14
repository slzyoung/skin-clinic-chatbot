import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { RiAlertLine, RiBuildingLine, RiChat1Line, RiCheckLine } from "@remixicon/react";
import { format } from "date-fns";
import Link from "next/link";
import { FeedbackNotification } from "../api/types";

interface NotificationItemProps {
	item: FeedbackNotification;
	onMarkAsRead: (id: string) => void;
}

function formatTimestamp(dateString: string) {
	try {
		return format(new Date(dateString), "MMM d, yyyy • h:mm a");
	} catch {
		return dateString;
	}
}

export function NotificationItem({ item, onMarkAsRead }: NotificationItemProps) {
	const isUnread = !item.is_feedback_read;

	return (
		<div
			className={cn(
				"border rounded-md p-3.5 flex flex-col gap-2.5 transition-all text-xs",
				isUnread
					? "bg-amber-50/40 border-amber-200 hover:border-amber-300"
					: "bg-white border-gray-200/80 hover:border-gray-300",
			)}
		>
			{/* Top Row: Doctor Info, Badges, Timestamp & Action */}
			<div className="flex items-center justify-between gap-2">
				<div className="flex items-center gap-2 flex-wrap">
					<span className="font-semibold text-gray-900">{item.doctor || "Unknown Doctor"}</span>

					{item.doctor_type && (
						<span className="inline-flex items-center text-[10px] font-medium text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">
							{item.doctor_type}
						</span>
					)}

					{item.has_data_issue && (
						<span className="inline-flex items-center gap-1 text-[10px] font-medium text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded">
							<RiAlertLine className="size-2.5" />
							Missing Data
						</span>
					)}

					{isUnread && <span className="size-1.5 rounded-full bg-amber-500 inline-block" />}
				</div>

				<div className="flex items-center gap-2 shrink-0">
					<span className="text-[11px] text-muted-foreground">
						{formatTimestamp(item.updated_at)}
					</span>
					{isUnread && (
						<Button
							variant="ghost"
							size="sm"
							onClick={() => onMarkAsRead(item.id)}
							className="h-6 px-1.5 text-[11px] text-amber-800 hover:text-amber-950 hover:bg-amber-100/70 font-medium"
							title="Mark as read"
						>
							<RiCheckLine className="size-3 mr-0.5" />
							Mark read
						</Button>
					)}
				</div>
			</div>

			{/* Middle Row: Feedback Message */}
			<div className="text-xs leading-relaxed">
				{item.feedback ? (
					<p className={isUnread ? "text-amber-950 font-normal" : "text-gray-700 font-normal"}>
						{item.feedback}
					</p>
				) : (
					<p className="text-muted-foreground italic text-[11px]">No written comment provided.</p>
				)}
			</div>

			{/* Bottom Row: Chat Session & Branch Metadata */}
			<div className="flex items-center gap-3 flex-wrap pt-0.5 text-[11px] text-gray-700">
				<span className="inline-flex items-center gap-1 font-medium text-gray-600">
					<RiBuildingLine className="size-3 text-gray-500" />
					{item.branch || "Unknown Branch"}
				</span>

				<Link
					href={`/dashboard/chat-history/${item.id}`}
					className="inline-flex items-center gap-1 text-gray-600 hover:text-gray-900 transition-colors cursor-pointer"
					title="View chat session details"
				>
					<RiChat1Line className="size-3 text-gray-500" />
					<span>Session:</span>
					<span className="font-mono font-medium text-gray-800 hover:text-black break-all">
						{item.id}
					</span>
				</Link>
			</div>
		</div>
	);
}
