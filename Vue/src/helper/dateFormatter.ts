const formatDate = (dateString: string): string => {
  const date = new Date(dateString);

  return new Intl.DateTimeFormat('de-DE', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Europe/Berlin',
  })
    .format(date)
    .replaceAll('.', '.\u200B');
};

export { formatDate };
