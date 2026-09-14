import { Skeleton } from "@/components/ui/skeleton";

interface NotificationListSkeletonProps {
	count?: number;
}

export function NotificationListSkeleton({ count = 4 }: NotificationListSkeletonProps) {
	return (
		<div className="flex flex-col gap-2">
			{[...Array(count)].map((_, i) => (
				<div
					key={i}
					className="bg-white border border-gray-100 rounded-md p-3 flex items-start gap-3"
				>
					<Skeleton className="size-7 rounded-full shrink-0" />
					<div className="flex-1 space-y-1.5">
						<div className="flex items-center justify-between">
							<Skeleton className="h-3.5 w-32" />
							<Skeleton className="h-3 w-24" />
						</div>
						<Skeleton className="h-3 w-full" />
					</div>
				</div>
			))}
		</div>
	);
}
