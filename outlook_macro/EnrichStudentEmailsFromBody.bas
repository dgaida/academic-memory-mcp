' =============================================================================
' EnrichStudentEmailsFromBody.bas
' Outlook 2019 VBA-Makro
'
' Funktionsweise:
'   1. Liest students.yaml ein.
'   2. Durchlaeuft E-Mails und sucht Namen im Textkoerper.
'   3. Findet neue E-Mail-Adressen fuer bekannte Studierende.
'   4. Schreibt die YAML-Datei mit den neuen Adressen zurueck.
'
' YAML-Format:
'   students:
'   - name: Max Mustermann
'     smail: m.mustermann@smail.th-koeln.de
'     emails:
'     - max@privat.de
'     folders: []
' =============================================================================

Option Explicit

Private Const YAML_FILE_PATH As String = "D:\TH_Koeln\academic-memory-mcp\students.yaml"

''' Hauptprozedur: Findet neue Adressen durch Namenssuche in Mails.
Public Sub EnrichStudentEmails()
    Dim students As Collection
    Set students = ReadStudents(YAML_FILE_PATH)
    
    If students Is Nothing Then Exit Sub

    Dim inbox As Outlook.MAPIFolder
    Dim sentItems As Outlook.MAPIFolder
    Set inbox = Application.Session.GetDefaultFolder(olFolderInbox)
    Set sentItems = Application.Session.GetDefaultFolder(olFolderSentMail)

    Dim newFound As Long
    newFound = ScanFolderForNames(inbox, students, False)
    newFound = newFound + ScanFolderForNames(sentItems, students, True)

    If newFound > 0 Then
        WriteStudentsToYaml YAML_FILE_PATH, students
        MsgBox "Fertig! " & newFound & " neue Adressen gefunden und gespeichert.", vbInformation
    Else
        MsgBox "Keine neuen Adressen gefunden.", vbInformation
    End If
End Sub

''' Liest die Studierenden-Liste aus der YAML-Datei.
'''
''' Args:
'''     yamlPath: Pfad zur YAML-Datei.
'''
''' Returns:
'''     Collection von Student-Arrays.
Private Function ReadStudents(ByVal yamlPath As String) As Collection
    Dim result As New Collection
    Dim fileContent As String
    fileContent = ReadUtf8File(yamlPath)
    If Len(fileContent) = 0 Then Exit Function

    Dim allLines() As String
    allLines = Split(fileContent, vbLf)

    Dim sName As String, sSmail As String
    Dim dEmails As Object
    Dim inEmails As Boolean
    
    Dim i As Long
    For i = 0 To UBound(allLines)
        Dim line As String
        line = allLines(i)
        If Right(line, 1) = vbCr Then line = Left(line, Len(line) - 1)
        Dim trimmed As String
        trimmed = Trim(line)
        Dim indent As Long
        indent = Len(line) - Len(LTrim(line))

        If Left(trimmed, 2) = "- " And indent = 0 Then
            If Len(sName) > 0 Then result.Add Array(sName, sSmail, dEmails)
            sName = Replace(Trim(Mid(trimmed, 3)), """", "")
            If Left(sName, 5) = "name:" Then sName = Trim(Mid(sName, 6))
            sSmail = ""
            Set dEmails = CreateObject("Scripting.Dictionary")
            inEmails = False
        ElseIf Left(trimmed, 5) = "name:" And indent = 2 Then
            sName = Replace(Trim(Mid(trimmed, 6)), """", "")
        ElseIf Left(trimmed, 6) = "smail:" And indent = 2 Then
            sSmail = LCase(Replace(Trim(Mid(trimmed, 7)), """", ""))
        ElseIf Left(trimmed, 7) = "emails:" And indent = 2 Then
            If Trim(Mid(trimmed, 8)) <> "[]" Then inEmails = True Else inEmails = False
        ElseIf inEmails And Left(trimmed, 2) = "- " And indent = 2 Then
            Dim e As String
            e = LCase(Replace(Trim(Mid(trimmed, 3)), """", ""))
            If Len(e) > 0 Then dEmails(e) = True
        End If
    Next i
    If Len(sName) > 0 Then result.Add Array(sName, sSmail, dEmails)
    Set ReadStudents = result
End Function

''' Scannt einen Ordner nach bekannten Namen.
'''
''' Args:
'''     folder:   Ordner.
'''     students: Studierenden-Liste.
'''     isSent:   Ob gesendete Mails.
'''
''' Returns:
'''     Anzahl gefundener neuer Adressen.
Private Function ScanFolderForNames(ByVal folder As Outlook.MAPIFolder, ByVal students As Collection, ByVal isSent As Boolean) As Long
    Dim count As Long
    Dim items As Outlook.items
    Set items = folder.items
    Dim i As Long
    For i = 1 To items.count
        Dim item As Object
        Set item = items(i)
        If TypeOf item Is Outlook.mailItem Then
            Dim body As String
            body = item.body
            Dim s As Variant
            For Each s In students
                If InStr(1, body, s(0), vbTextCompare) > 0 Then
                    Dim addr As String
                    If isSent Then addr = GetFirstRecipientAddress(item) Else addr = GetSenderEmailAddress(item)
                    If Len(addr) > 0 And addr <> s(1) And Not s(2).Exists(addr) Then
                        s(2)(addr) = True
                        count = count + 1
                    End If
                End If
            Next s
        End If
    Next i
    ScanFolderForNames = count
End Function

''' Schreibt die Studierenden zurueck in die YAML.
'''
''' Args:
'''     yamlPath: Pfad.
'''     students: Liste.
Private Sub WriteStudentsToYaml(ByVal yamlPath As String, ByVal students As Collection)
    Dim lines() As String
    lines = ReadAllLines(yamlPath)
    
    Dim content As String
    content = "students:" & vbLf
    Dim s As Variant
    For Each s In students
        content = content & "- name: " & s(0) & vbLf
        content = content & "  smail: " & s(1) & vbLf
        If s(2).count = 0 Then
            content = content & "  emails: []" & vbLf
        Else
            content = content & "  emails:" & vbLf
            Dim e As Variant
            For Each e In s(2).Keys
                content = content & "  - " & e & vbLf
            Next e
        End If
        content = content & ExtractFoldersBlock(lines, CStr(s(1))) & vbLf
    Next s

    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.WriteText content
    stream.Position = 0
    stream.Type = 1
    stream.Position = 3
    Dim final As Object
    Set final = CreateObject("ADODB.Stream")
    final.Type = 1
    final.Open
    stream.CopyTo final
    final.SaveToFile yamlPath, 2
    stream.Close
    final.Close
End Sub

''' Extrahiert den folders-Block eines Studierenden aus der YAML.
'''
''' Args:
'''     lines: Zeilen der Datei.
'''     smail: E-Mail.
'''
''' Returns:
'''     Folders-Block als String.
Private Function ExtractFoldersBlock(ByRef lines() As String, ByVal smail As String) As String
    Dim i As Long, inStudent As Boolean, found As Boolean
    For i = 0 To UBound(lines)
        Dim trimmed As String
        trimmed = Trim(lines(i))
        Dim indent As Long
        indent = Len(lines(i)) - Len(LTrim(lines(i)))
        
        If Left(trimmed, 2) = "- " And indent = 0 Then
            inStudent = True
            found = False
        End If
        
        if inStudent Then
            If Left(trimmed, 6) = "smail:" And LCase(Replace(Trim(Mid(trimmed, 7)), """", "")) = smail Then
                found = True
            End If
            
            If found And Left(trimmed, 8) = "folders:" Then
                Dim result As String
                result = "  " & trimmed
                Dim j As Long
                For j = i + 1 To UBound(lines)
                    If Len(Trim(lines(j))) = 0 Then GoTo NextJ
                    Dim nextIndent As Long
                    nextIndent = Len(lines(j)) - Len(LTrim(lines(j)))
                    If nextIndent = 0 Then Exit For
                    result = result & vbLf & lines(j)
NextJ:
                Next j
                ExtractFoldersBlock = result
                Exit Function
            End If
        End If
    Next i
    ExtractFoldersBlock = "  folders: []"
End Function

''' Liest eine UTF-8 Datei.
Private Function ReadUtf8File(ByVal filePath As String) As String
    On Error Resume Next
    Dim stream As Object
    Set stream = CreateObject("ADODB.Stream")
    stream.CharSet = "UTF-8"
    stream.Open
    stream.LoadFromFile filePath
    ReadUtf8File = stream.ReadText
    stream.Close
End Function

''' Liest alle Zeilen einer Datei.
Private Function ReadAllLines(ByVal filePath As String) As String()
    Dim content As String
    content = ReadUtf8File(filePath)
    ReadAllLines = Split(content, vbLf)
End Function

''' Ermittelt die Absender-E-Mail.
Private Function GetSenderEmailAddress(ByVal mail As Outlook.mailItem) As String
    On Error Resume Next
    GetSenderEmailAddress = LCase(mail.SenderEmailAddress)
End Function

''' Ermittelt die Empfaenger-E-Mail.
Private Function GetFirstRecipientAddress(ByVal mail As Outlook.mailItem) As String
    On Error Resume Next
    GetFirstRecipientAddress = LCase(mail.Recipients(1).Address)
End Function
