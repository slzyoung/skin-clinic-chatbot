"use client"

import { LoginForm } from "@/components/login-form"
import { RiRobot2Line } from "@remixicon/react"
import Image from "next/image"

export default function LoginPage() {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex justify-center gap-2 md:justify-start">
          <a href="#" className="flex items-center gap-2 font-medium">
            <div className="flex aspect-square size-10 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-500">
              <RiRobot2Line className="size-5" />
            </div>
            <div className="flex flex-col gap-1 leading-none">
              <span className="font-semibold text-blue-500 text-sm">ERHA</span>
              <span className="font-semibold text-blue-500 text-sm">Medical Assistant</span>
            </div>
          </a>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">
            <LoginForm />
          </div>
        </div>
      </div>
      <div className="relative hidden bg-muted lg:block">
        <Image
          src="/placeholder.svg"
          alt="Image"
          fill
          className="object-cover dark:brightness-[0.2] dark:grayscale"
        />
      </div>
    </div>
  )
}
