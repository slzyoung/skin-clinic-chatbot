"use client";

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { RiAddLine, RiImageAddLine, RiLoader4Line } from "@remixicon/react"
import { useCreateBranch } from "../hooks/use-branches"
import { useForm } from "@tanstack/react-form"
import { Field, FieldGroup, FieldLabel, FieldError } from "@/components/ui/field"
import { branchSchema, type BranchValues } from "./branch-schema"

export function AddBranchSheet() {
  const [open, setOpen] = React.useState(false)
  const createBranch = useCreateBranch()

  const form = useForm({
    defaultValues: {
      name: "",
      address: "",
      latitude: "",
      longitude: "",
      token_limit: "",
      image_url: "",
    } as any,
    validators: {
      onChange: branchSchema,
    },
    onSubmit: async ({ value, formApi }) => {
      // Parse with zod to ensure string numbers are transformed properly
      const parsedData = branchSchema.parse(value);

      createBranch.mutate({
        name: parsedData.name,
        address: parsedData.address,
        latitude: parsedData.latitude,
        longitude: parsedData.longitude,
        token_limit: parsedData.token_limit,
        image_url: parsedData.image_url,
      }, {
        onSuccess: () => {
          setOpen(false)
          formApi.reset()
        }
      })
    }
  })

  return (
    <>
      <Button 
        className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 font-medium"
        onClick={() => setOpen(true)}
      >
        <RiAddLine className="size-4 mr-2" />
        Add New Branch
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent className="sm:max-w-100 w-full p-0 flex flex-col gap-0 border-l border-black-50 bg-white">
          <SheetHeader className="p-4 border-b border-black-50">
            <SheetTitle className="text-base font-medium text-black-500 text-left">Add New Branch</SheetTitle>
          </SheetHeader>
        
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              e.stopPropagation();
              void form.handleSubmit();
            }}
            className="flex-1 flex flex-col overflow-hidden"
          >
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
              <FieldGroup>
                {/* Branch Picture */}
                <form.Field name="image_url">
                  {(field) => (
                    <div className="flex flex-col gap-2">
                      <FieldLabel htmlFor="image_url">Branch Picture</FieldLabel>
                      <div className="border border-dashed border-black-100 rounded-lg bg-zinc-50 p-6 flex flex-col items-center justify-center text-center gap-3">
                        <div className="size-10 rounded-full bg-white flex items-center justify-center border border-black-50 shadow-sm">
                          <RiImageAddLine className="size-5 text-black-300" />
                        </div>
                        <div className="flex flex-col gap-1">
                          <p className="text-sm">
                            <span className="font-medium text-black-500">Drag & Drop or </span>
                            <span className="font-medium text-blue-600 cursor-pointer hover:underline">Choose File</span>
                          </p>
                          <p className="text-xs text-black-300">Maximum file size: 5 MB</p>
                          <p className="text-xs text-black-300">Format file: .jpg, .jpeg, .png</p>
                        </div>
                      </div>
                    </div>
                  )}
                </form.Field>

                {/* Name */}
                <form.Field name="name">
                  {(field) => {
                    const isInvalid = field.state.meta.errors && field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel htmlFor="name">Name</FieldLabel>
                        <Input 
                          name={field.name}
                          id="name"
                          placeholder="Erha Gunung Kidul" 
                          className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500" 
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          aria-invalid={isInvalid}
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors as Array<{ message?: string }>} />
                        )}
                      </Field>
                    )
                  }}
                </form.Field>

                {/* Location */}
                <form.Field name="address">
                  {(field) => {
                    const isInvalid = field.state.meta.errors && field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel htmlFor="address">Location</FieldLabel>
                        <Textarea 
                          name={field.name}
                          id="address"
                          placeholder="Pakuwon Mall Jogja, Lantai 1..." 
                          className="min-h-30 rounded-lg border-black-50 bg-white text-sm text-black-500 resize-none p-3" 
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          aria-invalid={isInvalid}
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors as Array<{ message?: string }>} />
                        )}
                      </Field>
                    )
                  }}
                </form.Field>

                {/* Latitude & Longitude */}
                <div className="flex items-center gap-4">
                  <div className="flex flex-col gap-2 flex-1">
                    <form.Field name="latitude">
                      {(field) => {
                        const isInvalid = field.state.meta.errors && field.state.meta.errors.length > 0;
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel htmlFor="latitude">Latitude</FieldLabel>
                            <Input 
                              name={field.name}
                              id="latitude"
                              type="number"
                              step="any"
                              placeholder="-7.758" 
                              className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500" 
                              value={field.state.value}
                              onChange={(e) => field.handleChange(e.target.value)}
                              onBlur={field.handleBlur}
                              aria-invalid={isInvalid}
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors as Array<{ message?: string }>} />
                            )}
                          </Field>
                        )
                      }}
                    </form.Field>
                  </div>
                  <div className="flex flex-col gap-2 flex-1">
                    <form.Field name="longitude">
                      {(field) => {
                        const isInvalid = field.state.meta.errors && field.state.meta.errors.length > 0;
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel htmlFor="longitude">Longitude</FieldLabel>
                            <Input 
                              name={field.name}
                              id="longitude"
                              type="number"
                              step="any"
                              placeholder="110.395" 
                              className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500" 
                              value={field.state.value}
                              onChange={(e) => field.handleChange(e.target.value)}
                              onBlur={field.handleBlur}
                              aria-invalid={isInvalid}
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors as Array<{ message?: string }>} />
                            )}
                          </Field>
                        )
                      }}
                    </form.Field>
                  </div>
                </div>

                {/* Tokens */}
                <form.Field name="token_limit">
                  {(field) => {
                    const isInvalid = field.state.meta.errors && field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel htmlFor="token_limit">Tokens</FieldLabel>
                        <div className="relative">
                          <Input 
                            name={field.name}
                            id="token_limit"
                            type="number" 
                            placeholder="1000" 
                            className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" 
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            onBlur={field.handleBlur}
                            aria-invalid={isInvalid}
                          />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-black-200 pointer-events-none">
                            per month
                          </span>
                        </div>
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors as Array<{ message?: string }>} />
                        )}
                      </Field>
                    )
                  }}
                </form.Field>
              </FieldGroup>
            </div>

            <div className="p-4 border-t border-black-50 flex justify-end gap-3 bg-white">
              <Button 
                type="button"
                variant="outline" 
                className="border-blue-500 text-blue-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg font-medium px-5 shadow-none" 
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
              <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
                {([canSubmit, isSubmitting]) => (
                  <Button 
                    type="submit"
                    disabled={!canSubmit || createBranch.isPending || isSubmitting} 
                    className="bg-blue-600 text-white hover:bg-blue-700 rounded-lg font-medium px-5 shadow-none disabled:opacity-50 disabled:bg-black-50 disabled:text-black-200"
                  >
                    {(createBranch.isPending || isSubmitting) && (
                      <RiLoader4Line className="mr-2 h-4 w-4 animate-spin shrink-0" />
                    )}
                    {(createBranch.isPending || isSubmitting) ? "Adding..." : "Add Branch"}
                  </Button>
                )}
              </form.Subscribe>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </>
  )
}
