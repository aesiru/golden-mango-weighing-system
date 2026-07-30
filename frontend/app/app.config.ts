export default defineAppConfig({
  ui: {
    colors: {
      primary: 'green',
      neutral: 'slate'
    },
    calendar: {
      slots: {
        root: '',
        header: 'flex items-center justify-between',
        body: 'flex flex-col space-y-4 pt-4 sm:flex-row sm:space-x-4 sm:space-y-0',
        heading: 'text-center font-medium truncate mx-auto',
        grid: 'w-full border-collapse select-none space-y-1 focus:outline-none',
        gridRow: 'grid grid-cols-7 place-items-center',
        gridWeekDaysRow: 'mb-1 grid w-full grid-cols-7',
        gridBody: 'grid',
        headCell: 'rounded-md',
        headCellWeek: 'rounded-md text-muted',
        cell: 'relative text-center',
        cellTrigger: [
          'm-0.5 relative flex items-center justify-center rounded whitespace-nowrap focus-visible:ring-2 focus:outline-none data-disabled:text-muted data-unavailable:line-through data-unavailable:text-muted data-unavailable:pointer-events-none data-today:font-semibold data-[outside-view]:text-muted',
          'transition'
        ],
        cellWeek: 'relative text-center text-muted'
      },
      variants: {
        color: {
          primary: {
            headCell: 'text-primary',
            cellTrigger: 'focus-visible:ring-primary'
          },
          secondary: {
            headCell: 'text-secondary',
            cellTrigger: 'focus-visible:ring-secondary'
          },
          success: {
            headCell: 'text-success',
            cellTrigger: 'focus-visible:ring-success'
          },
          info: {
            headCell: 'text-info',
            cellTrigger: 'focus-visible:ring-info'
          },
          warning: {
            headCell: 'text-warning',
            cellTrigger: 'focus-visible:ring-warning'
          },
          error: {
            headCell: 'text-error',
            cellTrigger: 'focus-visible:ring-error'
          },
          neutral: {
            headCell: 'text-highlighted',
            cellTrigger: 'focus-visible:ring-inverted'
          }
        },
        variant: {
          solid: '',
          outline: '',
          soft: '',
          subtle: ''
        },
        size: {
          xs: {
            heading: 'text-xs',
            cell: 'text-xs',
            cellWeek: 'text-xs',
            headCell: 'text-[10px]',
            headCellWeek: 'text-[10px]',
            cellTrigger: 'size-7',
            body: 'space-y-2 pt-2'
          },
          sm: {
            heading: 'text-xs',
            headCell: 'text-xs',
            headCellWeek: 'text-xs',
            cellWeek: 'text-xs',
            cell: 'text-xs',
            cellTrigger: 'size-7'
          },
          md: {
            heading: 'text-sm',
            headCell: 'text-xs',
            headCellWeek: 'text-xs',
            cellWeek: 'text-xs',
            cell: 'text-sm',
            cellTrigger: 'size-8'
          },
          lg: {
            heading: 'text-md',
            headCell: 'text-md',
            headCellWeek: 'text-md',
            cellTrigger: 'size-9 text-md'
          },
          xl: {
            heading: 'text-lg',
            headCell: 'text-lg',
            headCellWeek: 'text-lg',
            cellTrigger: 'size-10 text-lg'
          }
        },
        weekNumbers: {
          true: {
            gridRow: 'grid-cols-8',
            gridWeekDaysRow: 'grid-cols-8 [&>*:first-child]:col-start-2'
          }
        }
      },
      compoundVariants: [
        {
          color: 'primary',
          variant: 'solid',
          class: {
            cellTrigger: 'data-[selected]:bg-primary data-[selected]:text-inverted data-today:not-data-[selected]:text-primary data-[highlighted]:bg-primary/20 hover:not-data-[selected]:bg-primary/20'
          }
        },
        {
          color: 'primary',
          variant: 'outline',
          class: {
            cellTrigger: 'data-[selected]:ring data-[selected]:ring-inset data-[selected]:ring-primary/50 data-[selected]:text-primary data-today:not-data-[selected]:text-primary data-[highlighted]:bg-primary/10 hover:not-data-[selected]:bg-primary/10'
          }
        },
        {
          color: 'primary',
          variant: 'soft',
          class: {
            cellTrigger: 'data-[selected]:bg-primary/10 data-[selected]:text-primary data-today:not-data-[selected]:text-primary data-[highlighted]:bg-primary/20 hover:not-data-[selected]:bg-primary/20'
          }
        },
        {
          color: 'primary',
          variant: 'subtle',
          class: {
            cellTrigger: 'data-[selected]:bg-primary/10 data-[selected]:text-primary data-[selected]:ring data-[selected]:ring-inset data-[selected]:ring-primary/25 data-today:not-data-[selected]:text-primary data-[highlighted]:bg-primary/20 hover:not-data-[selected]:bg-primary/20'
          }
        },
        {
          color: 'neutral',
          variant: 'solid',
          class: {
            cellTrigger: 'data-[selected]:bg-inverted data-[selected]:text-inverted data-today:not-data-[selected]:text-highlighted data-[highlighted]:bg-inverted/20 hover:not-data-[selected]:bg-inverted/10'
          }
        },
        {
          color: 'neutral',
          variant: 'outline',
          class: {
            cellTrigger: 'data-[selected]:ring data-[selected]:ring-inset data-[selected]:ring-accented data-[selected]:text-default data-[selected]:bg-default data-today:not-data-[selected]:text-highlighted data-[highlighted]:bg-inverted/10 hover:not-data-[selected]:bg-inverted/10'
          }
        },
        {
          color: 'neutral',
          variant: 'soft',
          class: {
            cellTrigger: 'data-[selected]:bg-elevated data-[selected]:text-default data-today:not-data-[selected]:text-highlighted data-[highlighted]:bg-inverted/20 hover:not-data-[selected]:bg-inverted/10'
          }
        },
        {
          color: 'neutral',
          variant: 'subtle',
          class: {
            cellTrigger: 'data-[selected]:bg-elevated data-[selected]:text-default data-[selected]:ring data-[selected]:ring-inset data-[selected]:ring-accented data-today:not-data-[selected]:text-highlighted data-[highlighted]:bg-inverted/20 hover:not-data-[selected]:bg-inverted/10'
          }
        }
      ],
      defaultVariants: {
        size: 'md',
        color: 'primary',
        variant: 'solid'
      }
    },
    input: {
      slots: {
        base: 'disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 disabled:cursor-not-allowed disabled:opacity-80 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700'
      }
    },
    textarea: {
      slots: {
        base: 'disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 disabled:cursor-not-allowed disabled:opacity-80 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700'
      }
    },
    select: {
      slots: {
        base: [
          'relative group rounded-md inline-flex items-center focus:outline-none disabled:cursor-not-allowed disabled:opacity-75 disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700',
          'transition-colors'
        ]
      }
    },
    selectMenu: {
      slots: {
        base: [
          'relative group rounded-md inline-flex items-center focus:outline-none disabled:cursor-not-allowed disabled:opacity-75 disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700',
          'transition-colors'
        ]
      },
      variants: {
        variant: {
          outline: 'text-highlighted bg-default ring ring-inset ring-accented hover:bg-elevated disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700',
          soft: 'text-highlighted bg-elevated/50 hover:bg-elevated focus:bg-elevated disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700',
          subtle: 'text-highlighted bg-elevated ring ring-inset ring-accented hover:bg-accented/75 disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700',
          ghost: 'text-highlighted bg-transparent hover:bg-elevated focus:bg-elevated disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700',
          none: 'text-highlighted bg-transparent disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700'
        }
      }
    },
    inputDate: {
      slots: {
        base: [
          'group relative inline-flex items-center rounded-md select-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-75 data-[disabled]:bg-gray-100 data-[disabled]:text-gray-500 data-[disabled]:border-gray-200 dark:data-[disabled]:bg-gray-800 dark:data-[disabled]:text-gray-400 dark:data-[disabled]:border-gray-700',
          'transition-colors'
        ],
        leading: 'absolute inset-y-0 start-0 flex items-center',
        leadingIcon: 'shrink-0 text-dimmed',
        leadingAvatar: 'shrink-0',
        leadingAvatarSize: '',
        trailing: 'absolute inset-y-0 end-0 flex items-center',
        trailingIcon: 'shrink-0 text-dimmed',
        segment: [
          'rounded text-center outline-hidden data-placeholder:text-dimmed data-[segment=literal]:text-muted data-invalid:text-error data-[disabled]:cursor-not-allowed data-[disabled]:opacity-75 data-[disabled]:bg-gray-100 data-[disabled]:text-gray-500 dark:data-[disabled]:bg-gray-800 dark:data-[disabled]:text-gray-400',
          'transition-colors'
        ],
        separatorIcon: 'shrink-0 size-4 text-muted'
      },
      variants: {
        variant: {
          outline: 'text-highlighted bg-default ring ring-inset ring-accented',
          soft: 'text-highlighted bg-elevated/50 hover:bg-elevated focus:bg-elevated disabled:bg-elevated/50',
          subtle: 'text-highlighted bg-elevated ring ring-inset ring-accented',
          ghost: 'text-highlighted bg-transparent hover:bg-elevated focus:bg-elevated disabled:bg-transparent dark:disabled:bg-transparent',
          none: 'text-highlighted bg-transparent'
        }
      }
    },
    inputTime: {
      slots: {
        base: [
          'group relative inline-flex items-center rounded-md select-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-75 data-[disabled]:bg-gray-100 data-[disabled]:text-gray-500 data-[disabled]:border-gray-200 dark:data-[disabled]:bg-gray-800 dark:data-[disabled]:text-gray-400 dark:data-[disabled]:border-gray-700',
          'transition-colors'
        ],
        leading: 'absolute inset-y-0 start-0 flex items-center',
        leadingIcon: 'shrink-0 text-dimmed',
        leadingAvatar: 'shrink-0',
        leadingAvatarSize: '',
        trailing: 'absolute inset-y-0 end-0 flex items-center',
        trailingIcon: 'shrink-0 text-dimmed',
        segment: [
          'rounded text-center outline-hidden data-placeholder:text-dimmed data-[segment=literal]:text-muted data-invalid:text-error data-[disabled]:cursor-not-allowed data-[disabled]:opacity-75 data-[disabled]:bg-gray-100 data-[disabled]:text-gray-500 dark:data-[disabled]:bg-gray-800 dark:data-[disabled]:text-gray-400',
          'transition-colors'
        ],
        separatorIcon: 'shrink-0 size-4 text-muted'
      },
      variants: {
        variant: {
          outline: 'text-highlighted bg-default ring ring-inset ring-accented',
          soft: 'text-highlighted bg-elevated/50 hover:bg-elevated focus:bg-elevated disabled:bg-elevated/50',
          subtle: 'text-highlighted bg-elevated ring ring-inset ring-accented',
          ghost: 'text-highlighted bg-transparent hover:bg-elevated focus:bg-elevated disabled:bg-transparent dark:disabled:bg-transparent',
          none: 'text-highlighted bg-transparent'
        }
      }
    },
    inputNumber: {
      slots: {
        root: 'relative inline-flex items-center',
        base: [
          'w-full rounded-md border-0 placeholder:text-dimmed focus:outline-none disabled:cursor-not-allowed disabled:opacity-75 disabled:bg-gray-100 disabled:text-gray-500 dark:disabled:bg-gray-800 dark:disabled:text-gray-400',
          'transition-colors'
        ],
        increment: 'absolute flex items-center',
        decrement: 'absolute flex items-center'
      }
    },
    checkbox: {
      slots: {
        base: 'disabled:bg-gray-100 disabled:text-gray-500 disabled:border-gray-200 disabled:cursor-not-allowed disabled:opacity-80 dark:disabled:bg-gray-800 dark:disabled:text-gray-400 dark:disabled:border-gray-700'
      }
    }
  }
})
