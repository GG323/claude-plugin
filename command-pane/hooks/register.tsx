import type { EngineInterface, Register } from 'claude-code'

// What the star button puts in the prompt box
const STAR_PROMPT = 'Build a skill based on our conversation, ask if the process to automate is not clear'

function fillPrompt($: EngineInterface) {
  void $.prompt.fill({ text: STAR_PROMPT, mode: 'replace' })
}

export const register: Register = on => {
  // Clear the todo status line an earlier version pinned
  on('session.start', async ($, e, next) => {
    $.ui.status(undefined)

    return next(e)
  })

  // Above the prompt: the band
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)

    const { Box, Text, Button } = $.ui.resolve(e)

    return (
      <Box flexDirection="row" gap={1}>
        <Button key="star-above" plain onPress={() => fillPrompt($)}>
          <Text color="warning">★</Text>
        </Button>
        <Text dimColor>Star prompt</Text>
      </Box>
    )
  })

}
