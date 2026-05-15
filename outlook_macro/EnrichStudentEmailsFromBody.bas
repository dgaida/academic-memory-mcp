' =============================================================================
' EnrichStudentEmailsFromBody.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Liest die YAML-Datei ein und laedt alle bekannten Studierenden
'      (Name + smail-Adresse).
'   2. Durchlaeuft alle E-Mails im Posteingang und in den Gesendeten Elementen.
'   3. Sucht im Betreff und Textkoerper jeder Mail nach dem Vor- und Nachnamen
'      jedes Studierenden (Format: "Vorname Nachname").
'   4. Findet er einen Treffer, wird die Absenderadresse (Eingang) bzw.
'      Empfaengeradresse (Gesendet) als zusaetzliche E-Mail-Adresse des
'      Studierenden in der YAML-Datei gespeichert - sofern sie nicht bereits
'      als smail oder in der emails-Liste steht.
'
' Voraussetzung:
'   Die YAML-Datei muss bereits durch CollectStudentEmails.bas erzeugt worden
'   sein und folgendes Format haben:
'
'     students:
'       - name: "Max Mustermann"
'         smail: "m.mustermann@smail.th-koeln.de"
'         emails: []          # oder: ["max@privat.de", ...]
'         folders: {}
'
' WICHTIG: Den Pfad zur YAML-Datei in YAML_FILE_PATH anpassen!
' =============================================================================

Option Explicit

Private Const YAML_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\students.yaml"

' =============================================================================
' Hauptprozedur
' =============================================================================

''' Durchsucht Posteingang und Gesendete nach Studentennamen und reichert
''' die YAML-Datei um zusaetzlich gefundene E-Mail-Adressen an.
Public Sub EnrichStudentEmailsFromBody()
    If Len(Dir(YAML_FILE_PATH)) = 0 Then
        MsgBox "YAML-Datei nicht gefunden:" & vbCrLf & YAML_FILE_PATH & vbCrLf & _
               "Bitte zuerst CollectStudentEmails ausfuehren.", _
               vbCritical, "EnrichStudentEmailsFromBody"
        Exit Sub
    End If

    ' Studierende aus YAML laden:
    ' students(i) = Array(name, smail, emails-Dictionary)
    Dim students As Collection
    Set students = LoadStudentsFromYaml(YAML_FILE_PATH)

    If students.Count = 0 Then
        MsgBox "Keine Studierenden in der YAML-Datei gefunden.", _
               vbExclamation, "EnrichStudentEmailsFromBody"
        Exit Sub
    End If

    Dim inbox     As Outlook.MAPIFolder
    Dim sentItems As Outlook.MAPIFolder
    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    Set sentItems = Application.Session.GetDefaultFolder(olFolderSentMail)

    Dim totalNew As Long
    totalNew = 0

    totalNew = totalNew + ScanFolderForNames(inbox, students, False)
    totalNew = totalNew + ScanFolderForNames(sentItems, students, True)

    If totalNew = 0 Then
        MsgBox "Keine neuen E-Mail-Adressen gefunden.", vbInformation, "EnrichStudentEmailsFromBody"
        Exit Sub
    End If

    ' Geaenderte YAML-Datei zurueckschreiben
    WriteStudentsToYaml YAML_FILE_PATH, students

    MsgBox "Fertig!" & vbCrLf & _
           totalNew & " neue E-Mail-Adresse(n) in YAML gespeichert.", _
           vbInformation, "EnrichStudentEmailsFromBody"
End Sub

' =============================================================================
' YAML einlesen
' =============================================================================

''' Laedt alle Studierenden aus der YAML-Datei in eine Collection.
'''
''' Jeder Eintrag in der Collection ist ein Array mit 3 Elementen:
'''   (0) name        As String
'''   (1) smail       As String  (Lowercase)
'''   (2) emailsDict  As Object  (Scripting.Dictionary, Lowercase-Keys)
'''
''' Args:
'''     yamlPath: Pfad zur YAML-Datei.
'''
''' Returns:
'''     Collection mit einem Array pro Studierenden.
Private Function LoadStudentsFromYaml(ByVal yamlPath As String) As Collection
    Dim result As New Collection
    On Error GoTo ReadError

    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.LoadFromFile yamlPath
    Dim fileContent As String
    fileContent = stream.ReadText
    stream.Close
    If Left(fileContent, 1) = Chr(239) Then fileContent = Mid(fileContent, 4)

    Dim allLines() As String
    allLines = Split(fileContent, vbLf)

    Dim currentName   As String
    Dim currentSmail  As String
    Dim currentEmails As Object
    Dim inEntry       As Boolean
    Dim inEmails      As Boolean
    inEntry = False
    inEmails = False

    Dim iLine As Long
    For iLine = 0 To UBound(allLines)
        Dim line As String
        line = allLines(iLine)
        If Right(line, 1) = vbCr Then line = Left(line, Len(line) - 1)
        Dim trimmed As String
        trimmed = Trim(line)
        Dim lineIndent As Long
        lineIndent = Len(line) - Len(LTrim(line))

        ' Neuer Studierenden-Eintrag: beginnt mit "- " auf Indent 0
        If Left(trimmed, 2) = "- " And lineIndent = 0 Then
            If inEntry And Len(currentSmail) > 0 Then
                result.Add BuildStudentArray(currentName, currentSmail, currentEmails)
            End If
            currentName = ""
            currentSmail = ""
            Set currentEmails = CreateObject("Scripting.Dictionary")
            currentEmails.CompareMode = 1
            inEntry = True
            inEmails = False

            Dim afterDash As String
            afterDash = Trim(Mid(trimmed, 3))
            If Left(afterDash, 5) = "name:" Then
                currentName = ExtractYamlStringValue(afterDash, "name")
            End If

        ElseIf inEntry Then
            If Left(trimmed, 5) = "name:" Then
                currentName = ExtractYamlStringValue(trimmed, "name")
                inEmails = False
            ElseIf Left(trimmed, 6) = "smail:" Then
                currentSmail = LCase(ExtractYamlStringValue(trimmed, "smail"))
                inEmails = False
            ElseIf Left(trimmed, 7) = "emails:" Then
                Dim emailsRaw As String
                emailsRaw = Trim(Mid(trimmed, 8))
                If Left(emailsRaw, 1) = "[" Then
                    ' Inline: emails: []  oder  emails: ["a@b.de"]
                    ParseInlineEmailList emailsRaw, currentEmails
                    inEmails = False
                Else
                    inEmails = True
                End If
            ElseIf inEmails And Left(trimmed, 2) = "- " Then
                ' Block-Liste: - addr
                Dim blockAddr As String
                blockAddr = LCase(Trim(Mid(trimmed, 3)))
                If Len(blockAddr) > 0 And Not currentEmails.Exists(blockAddr) Then
                    currentEmails.Add blockAddr, True
                End If
            ElseIf Left(trimmed, 8) = "folders:" Or Left(trimmed, 5) = "path:" Or _
                   Left(trimmed, 5) = "keys:" Then
                inEmails = False
            End If
        End If
    Next iLine

    ' Letzten Eintrag speichern
    If inEntry And Len(currentSmail) > 0 Then
        result.Add BuildStudentArray(currentName, currentSmail, currentEmails)
    End If

    Set LoadStudentsFromYaml = result
    Exit Function

ReadError:
    Set LoadStudentsFromYaml = result
End Function

''' Erzeugt ein Student-Array aus Name, smail und emails-Dictionary.
'''
''' Args:
'''     sName:   Anzeigename des Studierenden.
'''     sSmail:  smail-Adresse (Lowercase).
'''     dEmails: Dictionary mit weiteren bekannten E-Mail-Adressen.
'''
''' Returns:
'''     Variant-Array(0..2).
Private Function BuildStudentArray(ByVal sName As String, _
                                   ByVal sSmail As String, _
                                   ByVal dEmails As Object) As Variant
    Dim arr(2) As Variant
    arr(0) = sName
    arr(1) = sSmail
    Set arr(2) = dEmails
    BuildStudentArray = arr
End Function

''' Extrahiert den String-Wert aus einer YAML-Zeile der Form  key: "value".
'''
''' Args:
'''     line:    Die YAML-Zeile (bereits getrimmt).
'''     keyName: Der Schlusselname (ohne Doppelpunkt).
'''
''' Returns:
'''     Den extrahierten Wert ohne Anfuehrungszeichen.
Private Function ExtractYamlStringValue(ByVal line As String, _
                                        ByVal keyName As String) As String
    Dim prefix As String
    prefix = keyName & ":"
    If Left(line, Len(prefix)) <> prefix Then
        ExtractYamlStringValue = ""
        Exit Function
    End If
    Dim val As String
    val = Trim(Mid(line, Len(prefix) + 1))
    val = Replace(val, """", "")
    ExtractYamlStringValue = Trim(val)
End Function

''' Parst eine YAML-Inline-Liste  ["a@b.de", "c@d.de"]  in ein Dictionary.
'''
''' Args:
'''     raw:    Der rohe String beginnend mit "[".
'''     target: Das Ziel-Dictionary, in das die Adressen eingetragen werden.
Private Sub ParseInlineEmailList(ByVal raw As String, ByVal target As Object)
    ' Klammern entfernen
    raw = Replace(raw, "[", "")
    raw = Replace(raw, "]", "")
    raw = Replace(raw, """", "")
    Dim parts() As String
    parts = Split(raw, ",")
    Dim p As Variant
    For Each p In parts
        Dim addr As String
        addr = LCase(Trim(CStr(p)))
        If Len(addr) > 0 And Not target.Exists(addr) Then
            target.Add addr, True
        End If
    Next p
End Sub

' =============================================================================
' Ordner durchsuchen
' =============================================================================

''' Durchsucht einen Outlook-Ordner nach Vor-/Nachnamen-Matches.
'''
''' Args:
'''     folder:   Der zu durchsuchende Outlook-Ordner.
'''     students: Collection mit Student-Arrays (siehe LoadStudentsFromYaml).
'''     isSent:   True = Empfaengeradresse verwenden, False = Absenderadresse.
'''
''' Returns:
'''     Anzahl neu hinzugefuegter E-Mail-Adressen.
Private Function ScanFolderForNames(ByVal folder As Outlook.MAPIFolder, _
                                    ByVal students As Collection, _
                                    ByVal isSent As Boolean) As Long
    Dim newCount As Long
    newCount = 0

    Dim items As Outlook.items
    Set items = folder.items

    Dim i As Long
    For i = 1 To items.Count
        Dim item As Object
        Set item = items(i)

        If item.Class = olMail Then
            Dim searchText As String
            searchText = item.Subject & " " & item.Body

            Dim s As Variant
            For Each s In students
                Dim studentArr As Variant
                studentArr = s

                Dim fullName As String
                fullName = CStr(studentArr(0))
                If Len(fullName) = 0 Then GoTo NextStudent

                ' Nur pruefen wenn "Vorname Nachname" genau so im Text vorkommt
                If InStr(1, searchText, fullName, vbTextCompare) > 0 Then
                    Dim matchAddr As String
                    If isSent Then
                        matchAddr = LCase(GetFirstRecipientAddress(item))
                    Else
                        matchAddr = LCase(GetSenderEmailAddress(item))
                    End If

                    Dim smailAddr As String
                    smailAddr = CStr(studentArr(1))

                    Dim emailsDict As Object
                    Set emailsDict = studentArr(2)

                    ' Adresse hinzufuegen wenn nicht bereits bekannt
                    If Len(matchAddr) > 0 And _
                       matchAddr <> smailAddr And _
                       Not emailsDict.Exists(matchAddr) Then
                        emailsDict.Add matchAddr, True
                        newCount = newCount + 1
                    End If
                End If
NextStudent:
            Next s
        End If
    Next i

    ScanFolderForNames = newCount
End Function

' =============================================================================
' YAML schreiben
' =============================================================================

''' Schreibt die vollstaendige students-Collection zurueck in die YAML-Datei.
'''
''' Die Datei wird dabei komplett neu geschrieben (ueberschrieben). Alle
''' Felder ausser "name", "smail", "emails" und "folders" gehen verloren,
''' sofern sie nicht bereits hier beruecksichtigt werden.
'''
''' Args:
'''     yamlPath: Pfad zur YAML-Datei.
'''     students: Collection mit Student-Arrays.
Private Sub WriteStudentsToYaml(ByVal yamlPath As String, _
                                ByVal students As Collection)
    ' Bestehende Datei vollstaendig einlesen um den folders-Block zu erhalten
    Dim existingLines() As String
    existingLines = ReadAllLines(yamlPath)

    ' Neuen Inhalt als String aufbauen
    On Error GoTo WriteError
    Dim content As String
    content = "students:" & vbLf

    Dim s As Variant
    For Each s In students
        Dim studentArr As Variant
        studentArr = s

        Dim sName  As String
        Dim sSmail As String
        Dim dEmails As Object
        sName = CStr(studentArr(0))
        sSmail = CStr(studentArr(1))
        Set dEmails = studentArr(2)

        content = content & "- name: " & sName & vbLf
        content = content & "  smail: " & sSmail & vbLf

        ' emails-Liste
        If dEmails.Count = 0 Then
            content = content & "  emails: []" & vbLf
        Else
            content = content & "  emails:" & vbLf
            Dim eKey As Variant
            For Each eKey In dEmails.Keys
                content = content & "  - " & CStr(eKey) & vbLf
            Next eKey
        End If

        ' folders-Block aus der Originaldatei unveraendert uebernehmen
        Dim foldersBlock As String
        foldersBlock = ExtractFoldersBlock(existingLines, sSmail)
        If Len(foldersBlock) = 0 Then
            content = content & "  folders: []" & vbLf
        Else
            content = content & foldersBlock & vbLf
        End If

        content = content & vbLf
    Next s

    ' UTF-8 ohne BOM schreiben
    Dim streamOut As Object
    Set streamOut = CreateObject("ADODB.Stream")
    streamOut.CharSet = "UTF-8"
    streamOut.Open
    streamOut.WriteText content
    streamOut.Position = 0
    streamOut.Type = 1          ' adTypeBinary
    streamOut.Position = 3      ' UTF-8 BOM ueberspringen
    Dim streamFinal As Object
    Set streamFinal = CreateObject("ADODB.Stream")
    streamFinal.Type = 1
    streamFinal.Open
    streamOut.CopyTo streamFinal
    streamFinal.SaveToFile yamlPath, 2  ' adSaveCreateOverWrite
    streamOut.Close
    streamFinal.Close
    Exit Sub

WriteError:
    MsgBox "Fehler beim Schreiben der YAML-Datei: " & Err.Description, _
           vbCritical, "EnrichStudentEmailsFromBody"
End Sub

''' Liest alle Zeilen einer UTF-8-kodierten Textdatei in ein String-Array.
'''
''' Args:
'''     filePath: Pfad zur Datei.
'''
''' Returns:
'''     Array mit allen Zeilen (0-basiert), \r bereinigt.
Private Function ReadAllLines(ByVal filePath As String) As String()
    Dim lines() As String
    ReDim lines(0)

    On Error GoTo ReadErr
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.LoadFromFile filePath
    Dim content As String
    content = stream.ReadText
    stream.Close

    ' BOM entfernen falls vorhanden (UTF-8 BOM = EF BB BF)
    If Left(content, 1) = Chr(239) Then content = Mid(content, 4)

    lines = Split(content, vbLf)
    Dim i As Long
    For i = 0 To UBound(lines)
        If Right(lines(i), 1) = vbCr Then
            lines(i) = Left(lines(i), Len(lines(i)) - 1)
        End If
    Next i

ReadErr:
    ReadAllLines = lines
End Function

''' Extrahiert den "folders:"-Block eines bestimmten Studierenden aus den
''' Zeilen einer YAML-Datei (als rohen Text zum Wiedereinsetzen).
'''
''' Passend zum Format mit Einrueckung 0 fuer Studierenden-Eintraege:
'''   - name: ...        (Indent 0)
'''     smail: ...       (Indent 2)
'''     folders:         (Indent 2)
'''     - keys:          (Indent 2-4)
'''       - Keyword      (Indent 4-6)
'''       path: ...      (Indent 4-6)
'''
''' Args:
'''     lines:  Array aller Zeilen der YAML-Datei (ByRef, VBA-Pflicht fuer Arrays).
'''     smail:  Die smail-Adresse des gesuchten Studierenden (Lowercase).
'''
''' Returns:
'''     Den folders-Block als String (eine oder mehrere Zeilen mit fuehrendem
'''     Einzug), oder leerer String wenn nicht gefunden.
Private Function ExtractFoldersBlock(ByRef lines() As String, _
                                     ByVal smail As String) As String
    Dim i          As Long
    Dim foundSmail As Boolean
    Dim result     As String
    foundSmail = False

    For i = 0 To UBound(lines)
        Dim line As String
        line = lines(i)
        If Right(line, 1) = vbCr Then line = Left(line, Len(line) - 1)
        Dim trimmed As String
        trimmed = Trim(line)
        Dim lineIndent As Long
        lineIndent = Len(line) - Len(LTrim(line))

        ' Neuer Studierenden-Block beginnt: smail-Match zuruecksetzen
        If Left(trimmed, 2) = "- " And lineIndent = 0 Then
            If foundSmail Then Exit For  ' Naechster Student -> fertig
            foundSmail = False
        End If

        If Left(trimmed, 6) = "smail:" Then
            Dim lineAddr As String
            lineAddr = LCase(Trim(Replace(Mid(trimmed, 7), """", "")))
            If lineAddr = smail Then foundSmail = True
        End If

        If foundSmail And Left(trimmed, 8) = "folders:" Then
            Dim rest As String
            rest = Trim(Mid(trimmed, 9))
            If rest = "[]" Or rest = "" Then
                ' Leer: direkt zurueckgeben
                ExtractFoldersBlock = "  folders: []"
                Exit Function
            End If
            ' Mehrzeiliger Block: alle folgenden Zeilen mit Indent > 0 sammeln
            result = "  folders:" & vbLf
            Dim j As Long
            For j = i + 1 To UBound(lines)
                Dim nextLine As String
                nextLine = lines(j)
                If Right(nextLine, 1) = vbCr Then nextLine = Left(nextLine, Len(nextLine) - 1)
                Dim nextIndent As Long
                nextIndent = Len(nextLine) - Len(LTrim(nextLine))
                Dim nextTrimmed As String
                nextTrimmed = Trim(nextLine)
                ' Block endet beim naechsten Eintrag auf Indent 0 oder Leerzeile vor Indent 0
                If nextIndent = 0 And Len(nextTrimmed) > 0 Then Exit For
                result = result & nextLine & vbLf
            Next j
            ' Abschliessendes vbLf entfernen (wird in WriteStudentsToYaml angehaengt)
            If Right(result, Len(vbLf)) = vbLf Then
                result = Left(result, Len(result) - Len(vbLf))
            End If
            ExtractFoldersBlock = result
            Exit Function
        End If
    Next i

    ExtractFoldersBlock = ""
End Function

' =============================================================================
' Hilfsfunktionen (aus CollectStudentEmails / EmailSorter uebernommen)
' =============================================================================

''' Gibt die tatsaechliche SMTP-Adresse eines Absenders zurueck.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse (Lowercase).
Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String
    On Error GoTo Fallback
    Dim addrEntry As Outlook.AddressEntry
    Set addrEntry = mail.Sender
    If Not addrEntry Is Nothing Then
        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then
            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()
            If Not exchUser Is Nothing Then
                GetSenderEmailAddress = LCase(exchUser.PrimarySmtpAddress)
                Exit Function
            End If
        End If
    End If
Fallback:
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
End Function

''' Gibt die SMTP-Adresse des ersten Empfaengers zurueck.
'''
''' Args:
'''     mail: Das MailItem.
'''
''' Returns:
'''     SMTP-Adresse des ersten Empfaengers (Lowercase).
Private Function GetFirstRecipientAddress(ByVal mail As Outlook.mailItem) As String
    On Error GoTo RecipError
    If mail.Recipients.Count = 0 Then
        GetFirstRecipientAddress = ""
        Exit Function
    End If
    Dim recip     As Outlook.Recipient
    Dim addrEntry As Outlook.AddressEntry
    Set recip = mail.Recipients(1)
    Set addrEntry = recip.AddressEntry
    If Not addrEntry Is Nothing Then
        If addrEntry.AddressEntryUserType = olExchangeUserAddressEntry Or _
           addrEntry.AddressEntryUserType = olExchangeRemoteUserAddressEntry Then
            Dim exchUser As Outlook.ExchangeUser
            Set exchUser = addrEntry.GetExchangeUser()
            If Not exchUser Is Nothing Then
                GetFirstRecipientAddress = LCase(exchUser.PrimarySmtpAddress)
                Exit Function
            End If
        End If
    End If
RecipError:
    GetFirstRecipientAddress = LCase(recip.Address)
End Function
