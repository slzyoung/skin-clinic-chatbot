import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
	RiArrowDownSLine,
	RiFilterOffLine,
	RiMedicineBottleLine,
	RiUserLine,
} from "@remixicon/react";
import { NotificationFilterTab } from "../hooks/use-notifications-state";

interface NotificationFilterBarProps {
	activeTab: NotificationFilterTab;
	onTabChange: (tab: NotificationFilterTab) => void;
	totalCount: number;
	unreadCount: number;
	readCount: number;
	hasActiveFilters: boolean;
	onResetFilters: () => void;
	doctorFilter: string;
	onDoctorFilterChange: (doctor: string) => void;
	doctors: string[];
	doctorTypeFilter: string;
	onDoctorTypeFilterChange: (type: string) => void;
	doctorTypes: string[];
}

export function NotificationFilterBar({
	activeTab,
	onTabChange,
	totalCount,
	unreadCount,
	readCount,
	hasActiveFilters,
	onResetFilters,
	doctorFilter,
	onDoctorFilterChange,
	doctors,
	doctorTypeFilter,
	onDoctorTypeFilterChange,
	doctorTypes,
}: NotificationFilterBarProps) {
	return (
		<div className="flex flex-wrap items-center justify-between gap-2.5">
			{/* Left: Category Tabs */}
			<div className="flex items-center gap-1">
				<button
					type="button"
					onClick={() => onTabChange("all")}
					className={cn(
						"px-2.5 py-1 rounded-lg text-xs font-medium transition-colors",
						activeTab === "all"
							? "bg-gray-100 text-gray-900 font-semibold"
							: "text-muted-foreground hover:text-foreground hover:bg-gray-50",
					)}
				>
					All ({totalCount})
				</button>
				<button
					type="button"
					onClick={() => onTabChange("unread")}
					className={cn(
						"px-2.5 py-1 rounded-lg text-xs font-medium transition-colors",
						activeTab === "unread"
							? "bg-gray-100 text-gray-900 font-semibold"
							: "text-muted-foreground hover:text-foreground hover:bg-gray-50",
					)}
				>
					Unread ({unreadCount})
				</button>
				<button
					type="button"
					onClick={() => onTabChange("read")}
					className={cn(
						"px-2.5 py-1 rounded-lg text-xs font-medium transition-colors",
						activeTab === "read"
							? "bg-gray-100 text-gray-900 font-semibold"
							: "text-muted-foreground hover:text-foreground hover:bg-gray-50",
					)}
				>
					Read ({readCount})
				</button>
			</div>

			{/* Right: Dropdown Filters */}
			<div className="flex flex-wrap items-center gap-2">
				{/* Reset Filters button at the left */}
				{hasActiveFilters && (
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={onResetFilters}
						className="text-xs text-red-600 hover:text-red-700 bg-white hover:bg-red-50 border-red-200 hover:border-red-300 rounded-lg cursor-pointer h-9 px-3 gap-1.5 shadow-none transition-colors"
					>
						<RiFilterOffLine className="size-3.5 text-red-500" />
						Reset
					</Button>
				)}

				{/* Doctor Filter */}
				<DropdownMenu>
					<DropdownMenuTrigger
						render={
							<Button
								variant="outline"
								className="h-9 min-w-36 max-w-52 justify-between gap-1.5 bg-white font-normal text-zinc-700 hover:bg-zinc-50 border-gray-200 text-xs rounded-lg shadow-none cursor-pointer"
							/>
						}
					>
						<div className="flex items-center gap-1.5 truncate">
							<RiUserLine className="size-3.5 shrink-0 text-zinc-500" />
							<span className="truncate">
								{doctorFilter === "ALL" ? "All Doctors" : doctorFilter}
							</span>
						</div>
						<RiArrowDownSLine className="size-3.5 shrink-0 text-zinc-400" />
					</DropdownMenuTrigger>
					<DropdownMenuContent
						align="end"
						className="w-52 max-h-56 overflow-y-auto bg-white border border-gray-200 text-xs rounded-lg shadow-none"
					>
						<DropdownMenuRadioGroup value={doctorFilter} onValueChange={onDoctorFilterChange}>
							<DropdownMenuRadioItem closeOnClick value="ALL">
								All Doctors
							</DropdownMenuRadioItem>
							{doctors.map((doctor) => (
								<DropdownMenuRadioItem closeOnClick key={doctor} value={doctor}>
									{doctor}
								</DropdownMenuRadioItem>
							))}
						</DropdownMenuRadioGroup>
					</DropdownMenuContent>
				</DropdownMenu>

				{/* Doctor Type Filter */}
				<DropdownMenu>
					<DropdownMenuTrigger
						render={
							<Button
								variant="outline"
								className="h-9 min-w-36 max-w-52 justify-between gap-1.5 bg-white font-normal text-zinc-700 hover:bg-zinc-50 border-gray-200 text-xs rounded-lg shadow-none cursor-pointer"
							/>
						}
					>
						<div className="flex items-center gap-1.5 truncate">
							<RiMedicineBottleLine className="size-3.5 shrink-0 text-zinc-500" />
							<span className="truncate">
								{doctorTypeFilter === "ALL" ? "All Doctor Types" : doctorTypeFilter}
							</span>
						</div>
						<RiArrowDownSLine className="size-3.5 shrink-0 text-zinc-400" />
					</DropdownMenuTrigger>
					<DropdownMenuContent
						align="end"
						className="w-52 max-h-56 overflow-y-auto bg-white border border-gray-200 text-xs rounded-lg shadow-none"
					>
						<DropdownMenuRadioGroup
							value={doctorTypeFilter}
							onValueChange={onDoctorTypeFilterChange}
						>
							<DropdownMenuRadioItem closeOnClick value="ALL">
								All Doctor Types
							</DropdownMenuRadioItem>
							{doctorTypes.map((type) => (
								<DropdownMenuRadioItem closeOnClick key={type} value={type}>
									{type}
								</DropdownMenuRadioItem>
							))}
						</DropdownMenuRadioGroup>
					</DropdownMenuContent>
				</DropdownMenu>
			</div>
		</div>
	);
}
