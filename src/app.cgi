#!/usr/bin/perl -w
#@HDR@	$Id$
#@HDR@		Copyright 2024 by
#@HDR@		Christopher Caldwell/Brightsands
#@HDR@		P.O. Box 401, Bailey Island, ME 04003
#@HDR@		All Rights Reserved
#@HDR@
#@HDR@	This software comprises unpublished confidential information
#@HDR@	of Brightsands and may not be used, copied or made available
#@HDR@	to anyone, except in accordance with the license under which
#@HDR@	it is furnished.
########################################################################
#	app.cgi
#
#	Software to help make generating visas for lots of countries
#	easier.
#
#	2024-04-19 - c.m.caldwell@alumni.unh.edu - Created
########################################################################

use strict;
use lib "/usr/local/lib/perl";
use cpi_file qw( fatal files_in read_file read_lines write_file );
use cpi_filename qw( filename_to_text text_to_filename );
use cpi_arguments qw( parse_arguments );
use cpi_cgi qw( CGIheader CGIreceive );
use cpi_setup qw( setup );
use cpi_user qw( admin_page logout_select );
use cpi_vars;

use Data::Dumper;

&setup( stderr=>"Visas", require_captcha=>1 );

# Put constants here

my $CACHE_DIR = "$cpi_vars::BASEDIR/cache";
my $USER_DIR = "$cpi_vars::BASEDIR/users";
my $LIBDIR = "$cpi_vars::BASEDIR/lib";
my $TEMPLATE_DIR = "$LIBDIR/templates";
my $TEMPLATE_EXT = "pdf";
my $TEMPLATE_DESCRIPTOR = "dsc";
my $LANGUAGELIST = "$LIBDIR/languages";
my $VARS_FILE = "$LIBDIR/vars.pl";
my $SEP = "=";
my $TRANS = "/bin/trans";
my $CPDF = "/usr/local/bin/cpdf";
my $ONCHANGE = " onChange='submit();'";

my @VAR_LIST;
my %VAR_HASH;

# Put variables here.

our @problems;
our %ARGS;
my $exit_stat = 0;
my $DEFAULT_LANGUAGE = "en";

#########################################################################
#	Setup arguments if CGI.						#
#########################################################################
sub CGI_arguments
    {
    &CGIreceive();
    }

#########################################################################
#	Return text of thing in proper language.			#
#########################################################################
my $translations = {};;
my $cache_file;
my %need_translation;
sub text_of
    {
    my( $thing, @specifiers ) = @_;
    if( !ref($thing) || ref($thing) ne "HASH" )
	{ return $thing; }
    elsif( ! $cpi_vars::FORM{Language} )
	{ return $thing->{$DEFAULT_LANGUAGE}; }
    elsif( $thing->{$cpi_vars::FORM{Language}} )
	{ return $thing->{$cpi_vars::FORM{Language}}; }
    else
	{
	my $lup = join($SEP, @specifiers, $thing->{$DEFAULT_LANGUAGE});

	if( ! $cache_file && -f ($cache_file="$CACHE_DIR/$cpi_vars::FORM{Language}") )
	    { eval( &read_file($cache_file) ); }
	return $translations->{$lup}
	    if( $translations && $translations->{$lup} );
	$need_translation{$lup} = 1;
	return "XL(($lup))";
	}
    }

#########################################################################
#	Apparently we need to do some translations.			#
#########################################################################
sub translator
    {
    my( $s ) = join("",@_);
    my @to_translate = keys %need_translation;
    if( @to_translate )
	{
	my @pieces;
	my $ind = 0;
	foreach my $piece ( @to_translate )
	    {
	    my $txt = $piece;
	    $txt =~ s/.*=//;
	    push( @pieces, $txt );
	    $translations->{$piece} = "[$piece]";
	    }
	my $cmd = join(" ",
	    $TRANS,"-b",
	    "-s",$DEFAULT_LANGUAGE,
	    "-t",$cpi_vars::FORM{Language},
	    ( map { "'$_'" } @pieces ),
	    "|" );
	my( $result ) = &read_file( $cmd );
	#print "Executing [$cmd] returned [$result].<br>\n";
	$ind = 0;
	grep($translations->{$to_translate[$ind++]}=$_, split(/\n/ms,$result));
#	foreach $_ ( split( /\n/ms, $result ) )
#	    {
#	    print "Setting [",$to_translate[$ind],"] to [$_]<br>\n";
#	    $translations->{$to_translate[$ind++]} = $_;
#	    }
	$Data::Dumper::Indent = 1;
	&write_file( $cache_file,
	    Data::Dumper->Dump( [$translations], [ "\$translations" ] ) );

	@pieces = ();
	foreach my $piece ( split(/(XL\(\(.*?\)\))/,$s) )
	    {
	    if( $piece !~ /^XL\(\((.*)\)\)$/ )
		{ push( @pieces, $piece ); }
	    else
		{ push( @pieces, $translations->{$1} ); }
	    }
	$s = join("",@pieces);
	}
    return $s;
    }

#########################################################################
#	Display one question.						#
#########################################################################
sub ask_question
    {
    my( $vp ) = @_;
    my $curname = $vp->{name};
    my $curval = ($cpi_vars::FORM{$curname} || "");
    my @s = (
	"</tr>\n<tr><th valign=top align=left>",
	&text_of( $vp->{prompt}, $vp->{name} ),
	"</th>\n<td valign=top>" );
    if( $vp->{options} )
	{
	my $is_multi = ( $vp->{noptions} || 0 ) != 1;
	my $is_select = 1;
	my $input_type;
	my %selected;

	if( $is_select )
	    {
	    my $sz = scalar( @{$vp->{options}} );
	    $sz = 10 if( $sz > 10 );
	    push( @s, "<select name=$curname $ONCHANGE size=$sz",
		( $is_multi?" multiple":"" ), ">" );
	    %selected = map {($_," selected")} split(/,/,$curval);
	    }
	else
	    {
	    %selected = map {($_," checked")} split(/,/,$curval);
	    $input_type = ( $is_multi ? "checkbox" : "radio" );
	    }
	foreach my $op ( @{$vp->{options}} )
	    {
	    my $optval = $op->{code} || $op->{$DEFAULT_LANGUAGE};
	    if( $is_select )
	    	{
		push( @s,
		    "<option value='$optval'",($selected{$optval}||""),">",
		    &text_of( $op, $vp->{name}, $optval ), "</option>\n" );
		}
	    else
		{
		push( @s,
		    "<nobr><input name=$curname type=$input_type $ONCHANGE",
		    " value='$optval'", ($selected{$optval}||""),
		    ">", &text_of( $op, $vp->{name}, $optval ), "</nobr>\n" );
		}
	    }
	push( @s, "</select>" ) if( $is_select );
	}
    else
	{
	my $rows = $vp->{rows} || 1;
	my $cols = $vp->{cols} || 80;
	if( $rows == 1 )
	    {
	    push( @s,
		"<input name=$curname type=text $ONCHANGE",
		" size=$cols value='$curval'>" );
	    }
	else
	    {
	    push( @s,
		"</td></tr><tr><td colspan=2>",
		"<textarea name=$curname $ONCHANGE rows=$rows cols=$cols>",
		$curval, "</textarea>" );
	    }
	}
    push( @s, "</td>" );
    return @s;
    }

#########################################################################
#	Hide any previous answer to this question.			#
#########################################################################
sub hide_question
    {
    my( $vp ) = @_;
    my $curname = $vp->{name};
    my $curval = ($cpi_vars::FORM{$curname} || "");
    return "<input type=hidden name=$curname value='$curval'>";
    }

#########################################################################
#	True if, base on what we know, we'll definitely need the	#
#	answer.								#
#########################################################################
sub should_ask_question
    {
    my( $vp ) = @_;
    return 1 if( ! $vp->{positions} );
    return 0 if( ! $cpi_vars::FORM{Documents} );
    foreach my $document ( split(/,/,$cpi_vars::FORM{Documents}) )
	{
	return 1 if( $vp->{positions}{$document} );
	}
    return 0;
    }

#########################################################################
#########################################################################
sub generate_document
    {
    my $TMP_DIR = "$CACHE_DIR/generate";
    my @files_to_do;
    my @cmdpieces = ("rm -rf $TMP_DIR","mkdir -p $TMP_DIR");
    my $ind = 0;
    my $outfilename = "$TMP_DIR/done.pdf";
    foreach my $document ( split(/,/,$cpi_vars::FORM{togenerate}) )
	{
	my $filename = &text_to_filename($document).".$TEMPLATE_EXT";
	my $infilename = "$TEMPLATE_DIR/$filename";
        &fatal("Cannot read ${infilename}:  $!") if( ! -r $infilename );
	my $fnpiece = sprintf("%s/%03d",$TMP_DIR,$ind++);
	push( @cmdpieces,
	    "$CPDF -split ${infilename} -o $fnpiece.%%%.pdf -chunk 1");
	my %todos;
	foreach my $vp ( @VAR_LIST )
	    {
	    if( $vp->{positions} && $vp->{positions}{$document} )
		{
		my $val = $cpi_vars::FORM{ $vp->{name} } || "(".$vp->{name}.")";
		foreach my $cmd ( @{$vp->{positions}{$document}} )
		    {
		    my($page,$xpos,$ypos,$fontsize,$font) = split(/,/,$cmd);
		    $page ||= 1;
		    $xpos ||= 100;
		    $ypos ||= 100;
		    $fontsize ||= $ARGS{font_size};
		    push( @{$todos{$page}}, "-mtrans '$xpos $ypos'" );
		    push( @{$todos{$page}}, "-font-size $fontsize" )
			if($fontsize);
		    push( @{$todos{$page}}, "-font $font" )
			if($font);
		    push( @{$todos{$page}}, "-bt -text '$val' -et" );
		    }
		}
	    }
	foreach my $page ( keys %todos )
	    {
	    my $fn = sprintf("%s.%03d.pdf",$fnpiece,$page);
	    push( @cmdpieces,
		join(" ",
		    $CPDF,"-i $fn -draw",
			@{$todos{$page}},
			"-o $TMP_DIR/temp.pdf"),
		"mv $TMP_DIR/temp.pdf $fn");
	    }
	}
    push( @cmdpieces, "pdfunite $TMP_DIR/???.???.pdf $outfilename");
    #my $cmd = join(';<br><in>',@cmdpieces);
    system( join(';',@cmdpieces) );
    print "Content-type:  application/pdf\n\n",
	&read_file( $outfilename );
    exit(0);
    }

#########################################################################
#	These variables could be hard coded, but it's nicer to not	#
#	have to remember to update them.				#
#########################################################################
sub get_updated_var_list
    {
    eval( &read_file( $VARS_FILE ) );	# Get hard coded ones first
    grep( $VAR_HASH{$_->{name}} = $_, @VAR_LIST );

    my $first;
    my @languages;
    foreach $_ ( &read_lines( $LANGUAGELIST ) )
	{
	my( $code, $english, $native ) = split(/\s\s\s*/,$_);
	my $hp = {code=>$code, $DEFAULT_LANGUAGE=>$english, $code=>$native};
	if( $hp->{code} eq $DEFAULT_LANGUAGE )
	    { $first = $hp; }
	else
	    { push( @languages, $hp ); }
	}
    unshift( @languages,$first );	# Make en be first

    my @problems;
    my @documents;
    foreach my $fn ( &files_in( $TEMPLATE_DIR ) )
	{
	if( $fn =~ /^(\w.*)\.$TEMPLATE_EXT$/ )
	    {
	    my $txtname = $1;
	    my $descname = "$TEMPLATE_DIR/$1.$TEMPLATE_DESCRIPTOR";
	    if( ! open( INF, $descname ) )
		{ push( @problems, "No $descname for $TEMPLATE_DIR/$fn." ); }
	    else
		{
		my $document = &filename_to_text( $txtname );
		push( @documents, { $DEFAULT_LANGUAGE=>$document } );
		while( $_ = <INF> )
		    {
		    chomp( $_ );
		    my( $vname, @values ) = split(/\s+/);
		    $VAR_HASH{$vname}->{positions} ||= {};
		    $VAR_HASH{$vname}->{positions}->{$document} = \@values;
		    }
		close( INF );
		}
	    }
	}

    &fatal( @problems ) if @problems;

    $VAR_HASH{"Language"}->{options} = \@languages;
    $VAR_HASH{"Documents"}->{options} = \@documents;

    &write_file("$CACHE_DIR/hash", Dumper(\%VAR_HASH));
    &write_file("$CACHE_DIR/list", Dumper(\@VAR_LIST));
    }

#########################################################################
#	Generate a footer.						#
#########################################################################
sub gen_footer
    {
    my( $form_flag ) = @_;
    my @s;
    push( @s, "<table border=1 style='border-collapse:collapse'><tr><td>");
    if( $form_flag )
	{
	push( @s,
	    "<input type=button value='",
		&text_of({en=>"Update"}), "'",
		" onClick='disposition.value=\"Update\";submit();'>" )
	}
    else
	{
	push( @s,
	    "<input type=button value='",
		&text_of({en=>"Form"}), "'",
		" onClick='func.value=\"Redraw\";submit();'>" )
	}
    if( $cpi_vars::FORM{Documents} )
	{
	my @generateable_documents = ();
	push( @s, "<input type=hidden name=togenerate>" );
        foreach my $document ( split(/,/,$cpi_vars::FORM{Documents}) )
	    {
	    push( @s, "<input type=button value='",
	        &text_of( {en=>$document}, "generate" ), "'" );
	    if( ! -f "$TEMPLATE_DIR/".&text_to_filename($document).".$TEMPLATE_EXT" )
		{
		push( @s, " disabled" );
		}
	    else
		{
		push( @generateable_documents, $document );
		push( @s,
		    " onClick='togenerate.value=\"$document\";disposition.value=\"generate_document\";submit();'" );
		}
	    push( @s, ">" );
	    }
	push( @s, "<input type=button value='",
	    &text_of( {en=>"All"}, "generate" ), "' ",
	    ( ! @generateable_documents
	    ? "disabled"
	    : "onClick='togenerate.value=\"".join(",",@generateable_documents)."\";disposition.value=\"generate_document\";submit();'" ),
	    ">" );
	}
    push( @s,
	"<input type=button value='",
	    &text_of({en=>"Delete"}), "'",
	    " onClick='disposition.value=\"Delete\";submit();'>" )
	if( $form_flag );
    push( @s, &logout_select(), "</td></tr></table>" );
    return join("",@s);
    }

#########################################################################
#	Footer is called by cpi_user::admin_page			#
#########################################################################
sub footer( )
    {
    print "<form method=post><input type=hidden name=func>",
        &translator( join("",&gen_footer(0)) ),
	"</form>";
    }

#########################################################################
#	CGI mainline							#
#########################################################################
sub CGI_main
    {
    &get_updated_var_list();

    generate_document() if( $cpi_vars::FORM{disposition} eq "generate_document" );

    &CGIheader();

    print "</head>\n<body $cpi_vars::BODY_TAGS>";

    $cpi_vars::FORM{ind} ||= time();
    my $fn = "$USER_DIR/$cpi_vars::FORM{ind}";

#    foreach my $k ( keys %cpi_vars::FORM )
#	{
#	print "$k = [",$cpi_vars::FORM{$k},"]<br>\n";
#	}
    if( ! $cpi_vars::FORM{disposition} )
	{
	my $old_form;
	eval( &read_file( $fn ) ) if( -f $fn );
        grep( $cpi_vars::FORM{$_}=$old_form->{$_}, keys %{$old_form} )
	    if( $old_form );
	}
    elsif( $cpi_vars::FORM{disposition} eq "Update" )
	{
	print "Writing...<br>\n";
	delete $cpi_vars::FORM{disposition};
	$Data::Dumper::Indent = 1;
	&write_file( $fn, Data::Dumper->Dump( [\%cpi_vars::FORM], ["old_form"] ) );
	}
    elsif( $cpi_vars::FORM{func} eq "admin" )
	{
	&admin_page();
	&cleanup(0);
	}
    print "<hr>";

    my ( @s );
    push( @s, "<form name=form method=post><center>",
	"<input type=hidden name=func value=''>",
	"<input type=hidden name=disposition value=redraw>",
	"<input type=hidden name=ind value=$cpi_vars::FORM{ind}>",
	"<table border=1 cellspacing=1 cellpadding=5 style='border-collapse:collapse;border:solid;'><tr><th valign=top>",
	&text_of( {en=>"Question"} ),
	"</th><th valign=top>",
	&text_of( {en=>"Answer"} ),
	"</th>" );
    foreach my $vp ( @VAR_LIST )
    	{
	if( &should_ask_question($vp) )
	    { push(@s,&ask_question($vp)); }
	else
	    { push(@s,&hide_question($vp)); }
	}
    push( @s, "</tr>\n",
	"<tr><th colspan=2 align=center>", &gen_footer(1), "</th></tr>\n",
	"</table></center></form>" );
    print &translator( join("",@s) );
    }

#########################################################################
#	Ask the translation site for the list of languages we know.	#
#########################################################################
sub ask_for_language_list
    {
    open( INF, "$TRANS -list-all |" ) || die("Cannot generate listing:  $!");
    my $firstline;
    my @lines = ( "placeholder" );
    while( $_ = <INF> )
	{
	chomp( $_ );
	my( $code, $english, $native ) = split(/\s\s\s*/,$_);
	my $ln = "\t{code=>\"$code\", \"$DEFAULT_LANGUAGE\"=>\"$english\", \"$code\"=>\"$native\"}";
	if( $code eq $DEFAULT_LANGUAGE )
	    { $lines[0] = $ln; }
	else
	    { push( @lines, $ln ); }
	}
    shift(@lines) if ( $lines[0] eq "placeholder" );
    &write_file( "$cpi_vars::BASEDIR/lib/languages.pl",
        join(",\n",@lines) . "\n" );
    exit(0);
    }

#########################################################################
#	Command line mainline						#
#########################################################################
sub cmd_main
    {
    &ask_for_language_list();
    }

#########################################################################
#	Print usage message and die.					#
#########################################################################
sub usage
    {
    &fatal( @_, "",
	"Usage:  $cpi_vars::PROG <possible arguments>","",
	"where <possible arguments> is:",
	"    -f <font size>",
	"    <filename>"
	);
    }

#########################################################################
#	Main								#
#########################################################################

%ARGS = &parse_arguments({
    switches=>
	{
	"font_size"	=>	10,
	"verbosity"	=>	0
	}
    });

$cpi_vars::VERBOSITY = $ARGS{verbosity};

if( ! $ENV{SCRIPT_NAME} )
    { &cmd_main(); }
else
    { &CGI_arguments(); &CGI_main(); }

exit($exit_stat);
